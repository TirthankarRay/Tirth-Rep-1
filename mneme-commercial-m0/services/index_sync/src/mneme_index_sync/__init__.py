"""Mneme index-sync worker.

Watches the vault git repo, parses changed markdown files, chunks them
along heading boundaries, embeds each chunk locally, and upserts to
Postgres (files / chunks / edges).
"""
