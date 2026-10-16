# Persist an escalation before calling ServiceNow

Each conversation owns one support issue and at most one incident creation attempt at a time. Persist the accepted escalation and its audit event before calling ServiceNow, and use a stable correlation identifier to reconcile uncertain outcomes. PostgreSQL and ServiceNow cannot share a transaction: an uncertain result therefore remains pending verification instead of automatically retrying a create, trading automatic recovery speed for avoiding duplicate incidents.
