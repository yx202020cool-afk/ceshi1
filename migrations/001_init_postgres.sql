CREATE TABLE IF NOT EXISTS stocks (
    stock_code TEXT PRIMARY KEY,
    stock_name TEXT NOT NULL,
    exchange TEXT NOT NULL,
    board TEXT NOT NULL,
    listed_date TEXT NOT NULL,
    is_st BOOLEAN NOT NULL DEFAULT FALSE,
    is_delisting BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL
);

CREATE TABLE IF NOT EXISTS trading_calendar (
    trade_date DATE PRIMARY KEY,
    is_trading_day BOOLEAN NOT NULL,
    reason TEXT,
    created_at TIMESTAMPTZ NOT NULL
);

CREATE TABLE IF NOT EXISTS sectors (
    sector_code TEXT NOT NULL,
    sector_name TEXT NOT NULL,
    taxonomy TEXT NOT NULL,
    provider TEXT NOT NULL,
    classification_system TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL,
    PRIMARY KEY (sector_code, taxonomy, provider)
);

CREATE TABLE IF NOT EXISTS sector_constituents (
    sector_code TEXT NOT NULL,
    taxonomy TEXT NOT NULL,
    provider TEXT NOT NULL,
    stock_code TEXT NOT NULL,
    valid_from DATE NOT NULL,
    valid_to DATE,
    created_at TIMESTAMPTZ NOT NULL,
    PRIMARY KEY (sector_code, taxonomy, provider, stock_code, valid_from)
);

CREATE TABLE IF NOT EXISTS raw_quotes (
    id BIGSERIAL PRIMARY KEY,
    stock_code TEXT NOT NULL,
    trade_date DATE NOT NULL,
    as_of TIMESTAMPTZ NOT NULL,
    provider TEXT NOT NULL,
    close_price DOUBLE PRECISION,
    change_pct DOUBLE PRECISION,
    amount DOUBLE PRECISION,
    turnover_rate DOUBLE PRECISION,
    is_suspended BOOLEAN NOT NULL DEFAULT FALSE,
    data_status TEXT NOT NULL,
    quality_warnings TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    UNIQUE(stock_code, trade_date, as_of, provider)
);

CREATE TABLE IF NOT EXISTS sector_quotes (
    id BIGSERIAL PRIMARY KEY,
    sector_code TEXT NOT NULL,
    taxonomy TEXT NOT NULL,
    trade_date DATE NOT NULL,
    as_of TIMESTAMPTZ NOT NULL,
    provider TEXT NOT NULL,
    change_pct DOUBLE PRECISION,
    amount DOUBLE PRECISION,
    amount_change_pct DOUBLE PRECISION,
    up_count INTEGER,
    down_count INTEGER,
    flat_count INTEGER,
    limit_up_count INTEGER,
    limit_down_count INTEGER,
    break_limit_count INTEGER,
    median_change_pct DOUBLE PRECISION,
    data_status TEXT NOT NULL,
    quality_warnings TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    UNIQUE(sector_code, taxonomy, trade_date, as_of, provider)
);

CREATE TABLE IF NOT EXISTS stock_money_flow (
    id BIGSERIAL PRIMARY KEY,
    stock_code TEXT NOT NULL,
    trade_date DATE NOT NULL,
    as_of TIMESTAMPTZ NOT NULL,
    provider TEXT NOT NULL,
    main_net_inflow DOUBLE PRECISION,
    super_large_net_inflow DOUBLE PRECISION,
    large_net_inflow DOUBLE PRECISION,
    medium_net_inflow DOUBLE PRECISION,
    small_net_inflow DOUBLE PRECISION,
    net_inflow_ratio DOUBLE PRECISION,
    data_status TEXT NOT NULL,
    quality_warnings TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    UNIQUE(stock_code, trade_date, as_of, provider)
);

CREATE TABLE IF NOT EXISTS sector_money_flow (
    id BIGSERIAL PRIMARY KEY,
    sector_code TEXT NOT NULL,
    taxonomy TEXT NOT NULL,
    trade_date DATE NOT NULL,
    as_of TIMESTAMPTZ NOT NULL,
    provider TEXT NOT NULL,
    main_net_inflow DOUBLE PRECISION,
    super_large_net_inflow DOUBLE PRECISION,
    large_net_inflow DOUBLE PRECISION,
    medium_net_inflow DOUBLE PRECISION,
    small_net_inflow DOUBLE PRECISION,
    net_inflow_ratio DOUBLE PRECISION,
    flow_3d DOUBLE PRECISION,
    flow_5d DOUBLE PRECISION,
    flow_10d DOUBLE PRECISION,
    flow_20d DOUBLE PRECISION,
    is_final BOOLEAN NOT NULL,
    comparable_across_dates BOOLEAN NOT NULL,
    comparable_across_sectors BOOLEAN NOT NULL,
    data_status TEXT NOT NULL,
    quality_warnings TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    UNIQUE(sector_code, taxonomy, trade_date, as_of, provider)
);

CREATE TABLE IF NOT EXISTS news (
    id TEXT PRIMARY KEY,
    provider TEXT NOT NULL,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    url TEXT,
    published_at TIMESTAMPTZ NOT NULL,
    related_sector_codes TEXT NOT NULL,
    related_stock_codes TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL
);

CREATE TABLE IF NOT EXISTS announcements (
    id TEXT PRIMARY KEY,
    provider TEXT NOT NULL,
    title TEXT NOT NULL,
    url TEXT,
    published_at TIMESTAMPTZ NOT NULL,
    related_stock_codes TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL
);

CREATE TABLE IF NOT EXISTS data_snapshots (
    snapshot_id TEXT PRIMARY KEY,
    provider TEXT NOT NULL,
    trade_date DATE NOT NULL,
    as_of TIMESTAMPTZ NOT NULL,
    report_type TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    payload_hash TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL
);

CREATE TABLE IF NOT EXISTS features (
    feature_id TEXT PRIMARY KEY,
    snapshot_id TEXT NOT NULL,
    feature_json TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL
);

CREATE TABLE IF NOT EXISTS leader_scores (
    score_id TEXT PRIMARY KEY,
    snapshot_id TEXT NOT NULL,
    sector_code TEXT NOT NULL,
    taxonomy TEXT NOT NULL,
    stock_code TEXT NOT NULL,
    total_score DOUBLE PRECISION NOT NULL,
    sub_scores_json TEXT NOT NULL,
    reason TEXT NOT NULL,
    risk_tips TEXT NOT NULL,
    invalidation TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL
);

CREATE TABLE IF NOT EXISTS lifecycle_results (
    result_id TEXT PRIMARY KEY,
    snapshot_id TEXT NOT NULL,
    sector_code TEXT NOT NULL,
    taxonomy TEXT NOT NULL,
    stage TEXT NOT NULL,
    confidence DOUBLE PRECISION NOT NULL,
    triggered_rules TEXT NOT NULL,
    missing_conditions TEXT NOT NULL,
    next_stage TEXT NOT NULL,
    invalidation TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL
);

CREATE TABLE IF NOT EXISTS watchlist (
    item_id TEXT PRIMARY KEY,
    snapshot_id TEXT NOT NULL,
    stock_code TEXT NOT NULL,
    stock_name TEXT NOT NULL,
    sector_code TEXT NOT NULL,
    taxonomy TEXT NOT NULL,
    candidate_type TEXT NOT NULL,
    total_score DOUBLE PRECISION NOT NULL,
    reasons TEXT NOT NULL,
    risks TEXT NOT NULL,
    invalidation TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL
);

CREATE TABLE IF NOT EXISTS reports (
    report_id TEXT PRIMARY KEY,
    trade_date DATE NOT NULL,
    report_type TEXT NOT NULL,
    report_version TEXT NOT NULL,
    is_final BOOLEAN NOT NULL,
    snapshot_id TEXT NOT NULL,
    config_version TEXT NOT NULL,
    weights_version TEXT NOT NULL,
    code_version TEXT NOT NULL,
    provider TEXT NOT NULL,
    data_status TEXT NOT NULL,
    quality_warnings TEXT NOT NULL,
    report_json TEXT NOT NULL,
    reproducible_key TEXT NOT NULL,
    generated_at TIMESTAMPTZ NOT NULL,
    UNIQUE(trade_date, report_type, reproducible_key)
);

CREATE TABLE IF NOT EXISTS report_files (
    id BIGSERIAL PRIMARY KEY,
    report_id TEXT NOT NULL,
    file_type TEXT NOT NULL,
    file_path TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    UNIQUE(report_id, file_type, file_path)
);

CREATE TABLE IF NOT EXISTS job_runs (
    run_id TEXT PRIMARY KEY,
    job_name TEXT NOT NULL,
    trade_date DATE NOT NULL,
    report_type TEXT,
    status TEXT NOT NULL,
    started_at TIMESTAMPTZ NOT NULL,
    ended_at TIMESTAMPTZ,
    message TEXT,
    created_at TIMESTAMPTZ NOT NULL
);

CREATE TABLE IF NOT EXISTS data_quality_issues (
    issue_id TEXT PRIMARY KEY,
    snapshot_id TEXT,
    provider TEXT NOT NULL,
    issue_type TEXT NOT NULL,
    severity TEXT NOT NULL,
    message TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL
);

CREATE TABLE IF NOT EXISTS provider_health (
    provider_name TEXT PRIMARY KEY,
    status TEXT NOT NULL,
    mode TEXT NOT NULL,
    last_success_at TIMESTAMPTZ,
    last_error_at TIMESTAMPTZ,
    last_error TEXT,
    uses_demo_data BOOLEAN NOT NULL,
    is_final BOOLEAN NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL
);

CREATE TABLE IF NOT EXISTS config_versions (
    config_hash TEXT PRIMARY KEY,
    config_json TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_reports_trade_date ON reports(trade_date, report_type);
CREATE INDEX IF NOT EXISTS idx_sector_quotes_rank ON sector_quotes(trade_date, taxonomy, provider);
CREATE INDEX IF NOT EXISTS idx_money_flow_sector ON sector_money_flow(trade_date, taxonomy, provider);
CREATE INDEX IF NOT EXISTS idx_leader_sector ON leader_scores(snapshot_id, sector_code, taxonomy);
