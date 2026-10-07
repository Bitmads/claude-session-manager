"""YouTrack adapter for csm. REST API:
https://www.jetbrains.com/help/youtrack/devportal/operations-api-issues.html

Connection config:
    { "type": "youtrack", "url": "https://example.youtrack.cloud",
      "token_env": "YOUTRACK_TOKEN", "prefixes": ["VIS", "BIT"] }
Folder scope = project short name (e.g. "VIS"); limits search/recent to it.
Auth: permanent token, "Authorization: Bearer perm:...".
"""

from datetime import datetime, timezone

FIELDS = ("idReadable,summary,description,updated,resolved,project(shortName),"
          "customFields(name,value(name,fullName,login))")


class YouTrack:
    kind = "youtrack"

    def __init__(self, options, http):
        self.base = options.get("url", "").rstrip("/")
        if not self.base:
            raise ValueError('youtrack connection needs "url"')
        self.headers = {"Authorization": f"Bearer {options.get('token', '')}"}
        self.http = http

    def _get(self, path, params=None):
        return self.http.get_json(f"{self.base}/api/{path}", params=params, headers=self.headers)

    def _task(self, i):
        fields = {}
        for f in i.get("customFields") or []:
            v = f.get("value")
            if isinstance(v, list):
                v = v[0] if v else None
            if isinstance(v, dict):
                fields[f.get("name")] = v.get("fullName") or v.get("name") or v.get("login")
        updated = i.get("updated")
        if isinstance(updated, (int, float)):
            updated = datetime.fromtimestamp(updated / 1000, timezone.utc).isoformat()
        return {
            "key": i.get("idReadable"),
            "title": i.get("summary"),
            "url": f"{self.base}/issue/{i.get('idReadable')}",
            "status": fields.get("State") or ("Resolved" if i.get("resolved") else ""),
            "assignee": fields.get("Assignee"),
            "project": (i.get("project") or {}).get("shortName"),
            "description": i.get("description"),
            "updated": updated,
        }

    def get(self, key):
        try:
            return self._task(self._get(f"issues/{key}", {"fields": FIELDS}))
        except self.http.Error as e:
            if e.status == 404:
                return None
            raise

    def _query(self, query, limit):
        items = self._get("issues", {"query": query, "fields": FIELDS, "$top": limit})
        return [self._task(i) for i in items or []]

    @staticmethod
    def _scope(scope):
        return f"project: {scope} " if scope else ""

    def search(self, text, limit, scope=None):
        return self._query(f"{self._scope(scope)}{text}", limit)

    def recent(self, limit, scope=None):
        return self._query(f"{self._scope(scope)}#Unresolved sort by: updated desc", limit)

    def whoami(self):
        me = self._get("users/me", {"fields": "login,fullName"})
        return me.get("fullName") or me.get("login")


ADAPTERS = [YouTrack]
