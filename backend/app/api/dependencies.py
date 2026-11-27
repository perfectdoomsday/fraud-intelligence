from app.auth.security import require_permission

can_read = require_permission("read")
can_ingest = require_permission("ingest")
can_investigate = require_permission("investigate")
can_manage_models = require_permission("manage_models")
