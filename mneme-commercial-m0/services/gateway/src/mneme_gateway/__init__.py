"""Mneme MCP gateway.

The only contract agents speak to the vault through. Seven tools:
search, read, list, related, history, propose_edit, proposal_status.

Authentication in M0 is the trusted `X-Mneme-User` header. OAuth/OIDC
belongs to M3.
"""
