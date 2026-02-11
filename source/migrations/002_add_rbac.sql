-- RBAC Schema for Repository Access Control
-- This adds User Group-based permissions to the RAG system

-- 1. User Groups table
CREATE TABLE IF NOT EXISTS user_groups (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL UNIQUE,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. User to Group mapping (many-to-many)
CREATE TABLE IF NOT EXISTS user_group_members (
    id SERIAL PRIMARY KEY,
    user_identifier VARCHAR(255) NOT NULL,  -- username, email, or external ID
    group_id INTEGER NOT NULL REFERENCES user_groups(id) ON DELETE CASCADE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_identifier, group_id)
);

-- 3. Repository Permissions table
CREATE TABLE IF NOT EXISTS repository_permissions (
    id SERIAL PRIMARY KEY,
    group_id INTEGER NOT NULL REFERENCES user_groups(id) ON DELETE CASCADE,
    repository_id INTEGER NOT NULL REFERENCES repositories(id) ON DELETE CASCADE,
    permission_level VARCHAR(50) NOT NULL,  -- 'read', 'write', 'admin'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(group_id, repository_id)
);

-- 4. Indexes for performance
CREATE INDEX IF NOT EXISTS idx_user_group_members_user ON user_group_members(user_identifier);
CREATE INDEX IF NOT EXISTS idx_user_group_members_group ON user_group_members(group_id);
CREATE INDEX IF NOT EXISTS idx_repository_permissions_group ON repository_permissions(group_id);
CREATE INDEX IF NOT EXISTS idx_repository_permissions_repo ON repository_permissions(repository_id);

-- Sample Data
INSERT INTO user_groups (name, description) VALUES
    ('Finance', 'Finance team members'),
    ('Sales', 'Sales team members'),
    ('IT', 'IT administrators')
ON CONFLICT (name) DO NOTHING;

-- Sample mappings (adjust repository_ids as needed)
-- Finance group has access to Finance repository
INSERT INTO repository_permissions (group_id, repository_id, permission_level)
SELECT g.id, r.id, 'admin'
FROM user_groups g, repositories r
WHERE g.name = 'Finance' AND r.name LIKE '%Finance%'
ON CONFLICT DO NOTHING;

-- Sales group has access to Sales repository
INSERT INTO repository_permissions (group_id, repository_id, permission_level)
SELECT g.id, r.id, 'write'
FROM user_groups g, repositories r
WHERE g.name = 'Sales' AND r.name LIKE '%Sales%'
ON CONFLICT DO NOTHING;

-- Finance group ALSO has access to Sales repository (as requested)
INSERT INTO repository_permissions (group_id, repository_id, permission_level)
SELECT g.id, r.id, 'read'
FROM user_groups g, repositories r
WHERE g.name = 'Finance' AND r.name LIKE '%Sales%'
ON CONFLICT DO NOTHING;
