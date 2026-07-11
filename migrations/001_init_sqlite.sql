CREATE TABLE IF NOT EXISTS stocks (
    stock_code TEXT PRIMARY KEY,
    stock_name TEXT NOT NULL,
    exchange TEXT NOT NULL,
    board TEXT NOT NULL,
    listed_date TEXT NOT NULL,
    is_st INTEGER NOT NULL DEFAULT 0,
    is_delisting INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS trading_calendar (
    trade_date TEXT PRIMARY KEY,
    is_trading_day INTEGER NOT NULL,
    reason TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS sectors (
    sector_code TEXT NOT NULL,
    sector_name TEXT NOT NULL,
    taxonomy TEXT NOT NULL,
    provider TEXT NOT NULL,
    classification_system TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    PRIMARY KEY (sector_code, taxonomy, provider)
);

CREATE TABLE IF NOT EXISTS sector_constituents (
    sector_code TEXT NOT NULL,
    taxonomy TEXT NOT NULL,
    provider TEXT NOT NULL,
    stock_code TEXT NOT NULL,
    valid_from TEXT NOT NULL,
    valid_to TEXT,
    created_at TEXT NOT NULL,
    PRIMARY KEY (sector_code, taxonomy, provider, stock_code, valid_from)
);

CREATE TABLE IF NOT EXISTS raw_quotes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    stock_code TEXT NOT NULL,
    trade_date TEXT NOT NULL,
    as_of TEXT NOT NULL,
    provider TEXT NOT NULL,
    close_price REAL,
    change_pct REAL,
    amount REAL,
    turnover_rate REAL,
    is_suspended INTEGER NOT NULL DEFAULT 0,
    data_status TEXT NOT NULL,
    quality_warnings TEXT NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE(stock_code, trade_date, as_of, provider)
);

CREATE TABLE IF NOT EXISTS sector_quotes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sector_code TEXT NOT NULL,
    taxonomy TEXT NOT NULL,
    trade_date TEXT NOT NULL,
    as_of TEXT NOT NULL,
    provider TEXT NOT NULL,
    change_pct REAL,
    amount REAL,
    amount_change_pct REAL,
    up_count INTEGER,
    down_count INTEGER,
    flat_count INTEGER,
    limit_up_count INTEGER,
    limit_down_count INTEGER,
    break_limit_count INTEGER,
    median_change_pct REAL,
    data_status TEXT NOT NULL,
    quality_warnings TEXT NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE(sector_code, taxonomy, trade_date, as_of, provider)
);

CREATE TABLE IF NOT EXISTS stock_money_flow (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    stock_code TEXT NOT NULL,
    trade_date TEXT NOT NULL,
    as_of TEXT NOT NULL,
    provider TEXT NOT NULL,
    main_net_inflow REAL,
    super_large_net_inflow REAL,
    large_net_inflow REAL,
    medium_net_inflow REAL,
    small_net_inflow REAL,
    net_inflow_ratio REAL,
    data_status TEXT NOT NULL,
    quality_warnings TEXT NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE(stock_code, trade_date, as_of, provider)
);

CREATE TABLE IF NOT EXISTS sector_money_flow (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sector_code TEXT NOT NULL,
    taxonomy TEXT NOT NULL,
    trade_date TEXT NOT NULL,
    as_of TEXT NOT NULL,
    provider TEXT NOT NULL,
    main_net_inflow REAL,
    super_large_net_inflow REAL,
    large_net_inflow REAL,
    medium_net_inflow REAL,
    small_net_inflow REAL,
    net_inflow_ratio REAL,
    flow_3d REAL,
    flow_5d REAL,
    flow_10d REAL,
    flow_20d REAL,
    is_final INTEGER NOT NULL,
    comparable_across_dates INTEGER NOT NULL,
    comparable_across_sectors INTEGER NOT NULL,
    data_status TEXT NOT NULL,
    quality_warnings TEXT NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE(sector_code, taxonomy, trade_date, as_of, provider)
);

CREATE TABLE IF NOT EXISTS news (
    id TEXT PRIMARY KEY,
    provider TEXT NOT NULL,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    url TEXT,
    published_at TEXT NOT NULL,
    related_sector_codes TEXT NOT NULL,
    related_stock_codes TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS announcements (
    id TEXT PRIMARY KEY,
    provider TEXT NOT NULL,
    title TEXT NOT NULL,
    url TEXT,
    published_at TEXT NOT NULL,
    related_stock_codes TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS data_snapshots (
    snapshot_id TEXT PRIMARY KEY,
    provider TEXT NOT NULL,
    trade_date TEXT NOT NULL,
    as_of TEXT NOT NULL,
    report_type TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    payload_hash TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS features (
    feature_id TEXT PRIMARY KEY,
    snapshot_id TEXT NOT NULL,
    feature_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS leader_scores (
    score_id TEXT PRIMARY KEY,
    snapshot_id TEXT NOT NULL,
    sector_code TEXT NOT NULL,
    taxonomy TEXT NOT NULL,
    stock_code TEXT NOT NULL,
    total_score REAL NOT NULL,
    sub_scores_json TEXT NOT NULL,
    reason TEXT NOT NULL,
    risk_tips TEXT NOT NULL,
    invalidation TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS lifecycle_results (
    result_id TEXT PRIMARY KEY,
    snapshot_id TEXT NOT NULL,
    sector_code TEXT NOT NULL,
    taxonomy TEXT NOT NULL,
    stage TEXT NOT NULL,
    confidence REAL NOT NULL,
    triggered_rules TEXT NOT NULL,
    missing_conditions TEXT NOT NULL,
    next_stage TEXT NOT NULL,
    invalidation TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS watchlist (
    item_id TEXT PRIMARY KEY,
    snapshot_id TEXT NOT NULL,
    stock_code TEXT NOT NULL,
    stock_name TEXT NOT NULL,
    sector_code TEXT NOT NULL,
    taxonomy TEXT NOT NULL,
    candidate_type TEXT NOT NULL,
    total_score REAL NOT NULL,
    reasons TEXT NOT NULL,
    risks TEXT NOT NULL,
    invalidation TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS reports (
    report_id TEXT PRIMARY KEY,
    trade_date TEXT NOT NULL,
    report_type TEXT NOT NULL,
    report_version TEXT NOT NULL,
    is_final INTEGER NOT NULL,
    snapshot_id TEXT NOT NULL,
    config_version TEXT NOT NULL,
    weights_version TEXT NOT NULL,
    code_version TEXT NOT NULL,
    provider TEXT NOT NULL,
    data_status TEXT NOT NULL,
    quality_warnings TEXT NOT NULL,
    report_json TEXT NOT NULL,
    reproducible_key TEXT NOT NULL,
    generated_at TEXT NOT NULL,
    UNIQUE(trade_date, report_type, reproducible_key)
);

CREATE TABLE IF NOT EXISTS report_files (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    report_id TEXT NOT NULL,
    file_type TEXT NOT NULL,
    file_path TEXT NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE(report_id, file_type, file_path)
);

CREATE TABLE IF NOT EXISTS job_runs (
    run_id TEXT PRIMARY KEY,
    job_name TEXT NOT NULL,
    trade_date TEXT NOT NULL,
    report_type TEXT,
    status TEXT NOT NULL,
    started_at TEXT NOT NULL,
    ended_at TEXT,
    message TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS data_quality_issues (
    issue_id TEXT PRIMARY KEY,
    snapshot_id TEXT,
    provider TEXT NOT NULL,
    issue_type TEXT NOT NULL,
    severity TEXT NOT NULL,
    message TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS provider_health (
    provider_name TEXT PRIMARY KEY,
    status TEXT NOT NULL,
    mode TEXT NOT NULL,
    last_success_at TEXT,
    last_error_at TEXT,
    last_error TEXT,
    uses_demo_data INTEGER NOT NULL,
    is_final INTEGER NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS config_versions (
    config_hash TEXT PRIMARY KEY,
    config_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_reports_trade_date ON reports(trade_date, report_type);
CREATE INDEX IF NOT EXISTS idx_sector_quotes_rank ON sector_quotes(trade_date, taxonomy, provider);
CREATE INDEX IF NOT EXISTS idx_money_flow_sector ON sector_money_flow(trade_date, taxonomy, provider);
CREATE INDEX IF NOT EXISTS idx_leader_sector ON leader_scores(snapshot_id, sector_code, taxonomy);
