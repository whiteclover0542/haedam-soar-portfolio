"""Build n8n credentials from .env and wire them into the workflow JSON before import.

The workflow files carry credential references by name only (id ""), and the HTTP nodes that call the
portal/ticket store carry none at all (import used to wipe them). Fixed ids make the wiring deterministic.
"""
import copy

CALLERS = ["haedam-s1", "haedam-s4", "haedam-s8-s10", "haedam-s12", "haedam-s7", "haedam-s7-live", "haedam-release", "haedam-h1"]
# HTTP Request nodes with Header Auth but no reference: which credential they need, by workflow id.
HTTP_HEADER_AUTH = {"haedamResultLog01": "ticket-store (C)",
                    "haedamPortalIp01": "haedam-portal-response",
                    "haedamAccountLock01": "haedam-portal-response",
                    "haedamPortalPosting01": "haedam-portal-response"}


def _id(name):
    return "hd" + "".join(ch for ch in name.title() if ch.isalnum())[:14]


def build_credentials(env):
    def need(key):
        if not env.get(key):
            raise KeyError(f"{key} missing from .env")
        return env[key]

    header = lambda name, header_name, key: {"id": _id(name), "name": name, "type": "httpHeaderAuth",
                                              "data": {"name": header_name, "value": need(key)}}
    creds = [header(f"{c} caller", "X-Haedam-Key", "N8N_WEBHOOK_KEY") for c in CALLERS]
    creds += [header("ticket-store (C)", "X-Response-Key", "TICKET_STORE_KEY"),
              header("haedam-portal-response", "X-Response-Key", "PORTAL_RESPONSE_KEY"),
              {"id": _id("haedam-pf-response D"), "name": "haedam-pf-response D", "type": "sshPrivateKey",
               "data": {"host": "10.250.0.1", "port": 22, "username": "admin",
                        "privateKey": need("PF_SSH_PRIVATE_KEY"), "passphrase": ""}}]
    return creds


def attach_credentials(workflow, creds):
    by_name = {c["name"]: c for c in creds}
    w = copy.deepcopy(workflow)
    for node in w["nodes"]:
        for ref in (node.get("credentials") or {}).values():
            if ref.get("name") in by_name:
                ref["id"] = by_name[ref["name"]]["id"]
        target = HTTP_HEADER_AUTH.get(w.get("id"))
        if target and node["type"].endswith("httpRequest") and node["parameters"].get("genericAuthType") == "httpHeaderAuth":
            node["credentials"] = {"httpHeaderAuth": {"id": by_name[target]["id"], "name": target}}
    return w
