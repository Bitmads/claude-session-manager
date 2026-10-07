"""Linear adapter for csm. GraphQL API: https://linear.app/developers/graphql

Connection config:
    { "type": "linear", "token_env": "LINEAR_API_KEY", "prefixes": ["SET"] }
Folder scope = team key (e.g. "SET"); limits search/recent to that team.
Auth: personal API key in the Authorization header, no "Bearer" prefix.
"""

API_URL = "https://api.linear.app/graphql"
FIELDS = "identifier title url description updatedAt state { name } assignee { name } team { key }"


class Linear:
    kind = "linear"

    def __init__(self, options, http):
        self.token = options.get("token", "")
        self.http = http

    def _query(self, query, variables=None):
        data = self.http.post_json(API_URL, {"query": query, "variables": variables or {}},
                                   headers={"Authorization": self.token})
        errors = (data or {}).get("errors")
        if errors:
            raise LinearError("; ".join(e.get("message", "unknown error") for e in errors))
        return data["data"]

    @staticmethod
    def _task(n):
        return {
            "key": n.get("identifier"),
            "title": n.get("title"),
            "url": n.get("url"),
            "status": (n.get("state") or {}).get("name"),
            "assignee": (n.get("assignee") or {}).get("name"),
            "project": (n.get("team") or {}).get("key"),
            "description": n.get("description"),
            "updated": n.get("updatedAt"),
        }

    @staticmethod
    def _team_filter(scope):
        return {"team": {"key": {"eq": scope}}} if scope else {}

    def get(self, key):
        try:
            data = self._query(f"query($id: String!) {{ issue(id: $id) {{ {FIELDS} }} }}", {"id": key})
        except LinearError as e:
            if "not found" in str(e).lower():
                return None
            raise
        return self._task(data["issue"]) if data.get("issue") else None

    def search(self, text, limit, scope=None):
        q = (f"query($term: String!, $first: Int, $filter: IssueFilter) "
             f"{{ searchIssues(term: $term, first: $first, filter: $filter) {{ nodes {{ {FIELDS} }} }} }}")
        data = self._query(q, {"term": text, "first": limit, "filter": self._team_filter(scope)})
        return [self._task(n) for n in data["searchIssues"]["nodes"]]

    def recent(self, limit, scope=None):
        flt = dict(self._team_filter(scope), state={"type": {"nin": ["completed", "canceled"]}})
        q = (f"query($first: Int, $filter: IssueFilter) "
             f"{{ issues(first: $first, filter: $filter, orderBy: updatedAt) {{ nodes {{ {FIELDS} }} }} }}")
        data = self._query(q, {"first": limit, "filter": flt})
        return [self._task(n) for n in data["issues"]["nodes"]]

    def whoami(self):
        return self._query("{ viewer { name } }")["viewer"]["name"]


class LinearError(Exception):
    pass


ADAPTERS = [Linear]
