/*
 Navicat Premium Dump SQL

 Source Server         : vm_Ubuntu_pg
 Source Server Type    : PostgreSQL
 Source Server Version : 160011 (160011)
 Source Host           : 192.168.182.128:5432
 Source Catalog        : db_20251106_analysis_a
 Source Schema         : public

 Target Server Type    : PostgreSQL
 Target Server Version : 160011 (160011)
 File Encoding         : 65001

 Date: 24/12/2025 00:08:55
*/


-- ----------------------------
-- Type structure for gtrgm
-- ----------------------------
DROP TYPE IF EXISTS "public"."gtrgm";
CREATE TYPE "public"."gtrgm" (
  INPUT = "public"."gtrgm_in",
  OUTPUT = "public"."gtrgm_out",
  INTERNALLENGTH = VARIABLE,
  CATEGORY = U,
  DELIMITER = ','
);
ALTER TYPE "public"."gtrgm" OWNER TO "postgres";

-- ----------------------------
-- Sequence structure for board_blacklist_id_seq
-- ----------------------------
DROP SEQUENCE IF EXISTS "public"."board_blacklist_id_seq";
CREATE SEQUENCE "public"."board_blacklist_id_seq" 
INCREMENT 1
MINVALUE  1
MAXVALUE 2147483647
START 1
CACHE 1;

-- ----------------------------
-- Sequence structure for daily_sector_data_id_seq
-- ----------------------------
DROP SEQUENCE IF EXISTS "public"."daily_sector_data_id_seq";
CREATE SEQUENCE "public"."daily_sector_data_id_seq" 
INCREMENT 1
MINVALUE  1
MAXVALUE 9223372036854775807
START 1
CACHE 1;

-- ----------------------------
-- Sequence structure for daily_stock_data_id_seq
-- ----------------------------
DROP SEQUENCE IF EXISTS "public"."daily_stock_data_id_seq";
CREATE SEQUENCE "public"."daily_stock_data_id_seq" 
INCREMENT 1
MINVALUE  1
MAXVALUE 9223372036854775807
START 1
CACHE 1;

-- ----------------------------
-- Sequence structure for ext_board_list_id_seq
-- ----------------------------
DROP SEQUENCE IF EXISTS "public"."ext_board_list_id_seq";
CREATE SEQUENCE "public"."ext_board_list_id_seq" 
INCREMENT 1
MINVALUE  1
MAXVALUE 9223372036854775807
START 1
CACHE 1;

-- ----------------------------
-- Sequence structure for ext_providers_id_seq
-- ----------------------------
DROP SEQUENCE IF EXISTS "public"."ext_providers_id_seq";
CREATE SEQUENCE "public"."ext_providers_id_seq" 
INCREMENT 1
MINVALUE  1
MAXVALUE 2147483647
START 1
CACHE 1;

-- ----------------------------
-- Sequence structure for operation_logs_id_seq
-- ----------------------------
DROP SEQUENCE IF EXISTS "public"."operation_logs_id_seq";
CREATE SEQUENCE "public"."operation_logs_id_seq" 
INCREMENT 1
MINVALUE  1
MAXVALUE 2147483647
START 1
CACHE 1;

-- ----------------------------
-- Sequence structure for roles_id_seq
-- ----------------------------
DROP SEQUENCE IF EXISTS "public"."roles_id_seq";
CREATE SEQUENCE "public"."roles_id_seq" 
INCREMENT 1
MINVALUE  1
MAXVALUE 2147483647
START 1
CACHE 1;

-- ----------------------------
-- Sequence structure for sectors_id_seq
-- ----------------------------
DROP SEQUENCE IF EXISTS "public"."sectors_id_seq";
CREATE SEQUENCE "public"."sectors_id_seq" 
INCREMENT 1
MINVALUE  1
MAXVALUE 9223372036854775807
START 1
CACHE 1;

-- ----------------------------
-- Sequence structure for system_configs_id_seq
-- ----------------------------
DROP SEQUENCE IF EXISTS "public"."system_configs_id_seq";
CREATE SEQUENCE "public"."system_configs_id_seq" 
INCREMENT 1
MINVALUE  1
MAXVALUE 2147483647
START 1
CACHE 1;

-- ----------------------------
-- Sequence structure for user_sessions_id_seq
-- ----------------------------
DROP SEQUENCE IF EXISTS "public"."user_sessions_id_seq";
CREATE SEQUENCE "public"."user_sessions_id_seq" 
INCREMENT 1
MINVALUE  1
MAXVALUE 2147483647
START 1
CACHE 1;

-- ----------------------------
-- Sequence structure for users_id_seq
-- ----------------------------
DROP SEQUENCE IF EXISTS "public"."users_id_seq";
CREATE SEQUENCE "public"."users_id_seq" 
INCREMENT 1
MINVALUE  1
MAXVALUE 2147483647
START 1
CACHE 1;

-- ----------------------------
-- Table structure for board_blacklist
-- ----------------------------
DROP TABLE IF EXISTS "public"."board_blacklist";
CREATE TABLE "public"."board_blacklist" (
  "id" int4 NOT NULL DEFAULT nextval('board_blacklist_id_seq'::regclass),
  "keyword" varchar(50) COLLATE "pg_catalog"."default" NOT NULL,
  "level" varchar(20) COLLATE "pg_catalog"."default" DEFAULT 'BLACK'::character varying,
  "reason" varchar(100) COLLATE "pg_catalog"."default",
  "is_active" bool DEFAULT true,
  "created_at" timestamp(6) DEFAULT CURRENT_TIMESTAMP
)
;

-- ----------------------------
-- Table structure for cache_stock_board_signal
-- ----------------------------
DROP TABLE IF EXISTS "public"."cache_stock_board_signal";
CREATE TABLE "public"."cache_stock_board_signal" (
  "trade_date" date NOT NULL,
  "stock_code" varchar(10) COLLATE "pg_catalog"."default" NOT NULL,
  "stock_name" varchar(50) COLLATE "pg_catalog"."default",
  "market_rank" int4,
  "total_score" numeric(10,4),
  "signal_level" varchar(4) COLLATE "pg_catalog"."default",
  "final_score" numeric(10,4),
  "max_driver_board_id" int8,
  "max_driver_name" varchar(100) COLLATE "pg_catalog"."default",
  "max_driver_type" varchar(20) COLLATE "pg_catalog"."default",
  "max_driver_heat_pct" numeric(10,8),
  "primary_industry_id" int8,
  "primary_industry_name" varchar(100) COLLATE "pg_catalog"."default",
  "primary_industry_heat_pct" numeric(10,8),
  "industry_safe" bool,
  "board_exposure" numeric(10,6),
  "board_count" int4,
  "top_boards_json" text COLLATE "pg_catalog"."default",
  "snap_date" date,
  "created_at" timestamp(6) DEFAULT CURRENT_TIMESTAMP,
  "updated_at" timestamp(6) DEFAULT CURRENT_TIMESTAMP,
  "dna_json" text COLLATE "pg_catalog"."default",
  "final_score_pct" numeric(10,8),
  "fallback_reason" varchar(100) COLLATE "pg_catalog"."default"
)
;
COMMENT ON COLUMN "public"."cache_stock_board_signal"."signal_level" IS '板块信号等级: S(顶级) A(优秀) B(良好) NONE(无信号)';
COMMENT ON COLUMN "public"."cache_stock_board_signal"."final_score" IS '合成评分 = w_stock*总分 + w_exposure*共振 + w_max*最强概念 (行业不安全时*惩罚系数)';
COMMENT ON COLUMN "public"."cache_stock_board_signal"."industry_safe" IS '主营行业热度是否达标(>= board_safe_pct)';
COMMENT ON COLUMN "public"."cache_stock_board_signal"."snap_date" IS '稀疏快照寻址日期，可能早于trade_date';
COMMENT ON TABLE "public"."cache_stock_board_signal" IS '个股板块信号缓存表 - 每日ETL计算后写入';

-- ----------------------------
-- Table structure for daily_sector_data
-- ----------------------------
DROP TABLE IF EXISTS "public"."daily_sector_data";
CREATE TABLE "public"."daily_sector_data" (
  "id" int8 NOT NULL DEFAULT nextval('daily_sector_data_id_seq'::regclass),
  "sector_id" int8 NOT NULL,
  "date" date NOT NULL,
  "rank" int4 NOT NULL,
  "total_score" numeric(30,10),
  "open_price" numeric(30,10),
  "high_price" numeric(30,10),
  "low_price" numeric(30,10),
  "close_price" numeric(30,10),
  "price_change" numeric(30,10),
  "turnover_rate_percent" numeric(30,10),
  "volume_days" numeric(30,10),
  "avg_volume_ratio_50" numeric(30,10),
  "volume" int8,
  "volume_days_volume" numeric(30,10),
  "avg_volume_ratio_50_volume" numeric(30,10),
  "volatility" numeric(30,10),
  "volatile_consec" int4,
  "beta" numeric(30,10),
  "beta_consec" int4,
  "correlation" numeric(30,10),
  "long_term" numeric(30,10),
  "short_term" int4,
  "overbought" int4,
  "oversold" int4,
  "macd_signal" numeric(30,10),
  "slowkdj_signal" numeric(30,10),
  "lon_lonma" numeric(30,10),
  "lon_consec" int4,
  "lon_0" numeric(30,10),
  "loncons_consec" int4,
  "lonma_0" numeric(30,10),
  "lonmacons_consec" int4,
  "dma" numeric(30,10),
  "dma_consec" int4,
  "dif_dem" numeric(30,10),
  "macd_consec" int4,
  "dif_0" numeric(30,10),
  "macdcons_consec" int4,
  "dem_0" numeric(30,10),
  "demcons_consec" int4,
  "pdi_adx" numeric(30,10),
  "dmiadx_consec" int4,
  "pdi_ndi" numeric(30,10),
  "dmi_consec" int4,
  "obv" int8,
  "obv_consec" int4,
  "k_kdj" numeric(30,10),
  "slowkdj_consec" int4,
  "rsi" numeric(30,10),
  "rsi_consec" int4,
  "cci_neg_90" numeric(30,10),
  "cci_lower_consec" int4,
  "cci_pos_90" numeric(30,10),
  "cci_upper_consec" int4,
  "bands_lower" numeric(30,10),
  "bands_lower_consec" int4,
  "bands_middle" numeric(30,10),
  "bands_middle_consec" int4,
  "bands_upper" numeric(30,10),
  "bands_upper_consec" int4,
  "lon_lonma_diff" numeric(30,10),
  "lon" numeric(30,10),
  "lonma" numeric(30,10),
  "histgram" numeric(30,10),
  "dif" numeric(30,10),
  "dem" numeric(30,10),
  "adx" numeric(30,10),
  "plus_di" numeric(30,10),
  "obv_2" int8,
  "slowk" numeric(30,10),
  "rsi_2" numeric(30,10),
  "cci_neg_90_2" numeric(30,10),
  "cci_pos_90_2" numeric(30,10),
  "lower_band" numeric(30,10),
  "middle_band" numeric(30,10),
  "upper_band" numeric(30,10),
  "lst_close" numeric(30,10),
  "code2" varchar(20) COLLATE "pg_catalog"."default",
  "name2" varchar(50) COLLATE "pg_catalog"."default",
  "zhangdiefu2" numeric(30,10),
  "volume_consec2" numeric(30,10),
  "volume_50_consec2" numeric(30,10)
)
;

-- ----------------------------
-- Table structure for daily_stock_data
-- ----------------------------
DROP TABLE IF EXISTS "public"."daily_stock_data";
CREATE TABLE "public"."daily_stock_data" (
  "id" int8 NOT NULL DEFAULT nextval('daily_stock_data_id_seq'::regclass),
  "stock_code" varchar(10) COLLATE "pg_catalog"."default" NOT NULL,
  "date" date NOT NULL,
  "rank" int4 NOT NULL,
  "total_score" numeric(30,10),
  "open_price" numeric(30,10),
  "high_price" numeric(30,10),
  "low_price" numeric(30,10),
  "close_price" numeric(30,10),
  "jump" numeric(30,10),
  "price_change" numeric(30,10),
  "turnover_rate_percent" numeric(30,10),
  "volume_days" numeric(30,10),
  "avg_volume_ratio_50" numeric(30,10),
  "volume" int8,
  "volume_days_volume" numeric(30,10),
  "avg_volume_ratio_50_volume" numeric(30,10),
  "volatility" numeric(30,10),
  "volatile_consec" int4,
  "beta" numeric(30,10),
  "beta_consec" int4,
  "correlation" numeric(30,10),
  "market_cap_billions" numeric(30,10),
  "long_term" numeric(30,10),
  "short_term" int4,
  "overbought" int4,
  "oversold" int4,
  "macd_signal" numeric(30,10),
  "slowkdj_signal" numeric(30,10),
  "lon_lonma" numeric(30,10),
  "lon_consec" int4,
  "lon_0" numeric(30,10),
  "loncons_consec" int4,
  "lonma_0" numeric(30,10),
  "lonmacons_consec" int4,
  "dma" numeric(30,10),
  "dma_consec" int4,
  "dif_dem" numeric(30,10),
  "macd_consec" int4,
  "dif_0" numeric(30,10),
  "macdcons_consec" int4,
  "dem_0" numeric(30,10),
  "demcons_consec" int4,
  "pdi_adx" numeric(30,10),
  "dmiadx_consec" int4,
  "pdi_ndi" numeric(30,10),
  "dmi_consec" int4,
  "obv" int8,
  "obv_consec" int4,
  "k_kdj" numeric(30,10),
  "slowkdj_consec" int4,
  "rsi" numeric(30,10),
  "rsi_consec" int4,
  "cci_neg_90" numeric(30,10),
  "cci_lower_consec" int4,
  "cci_pos_90" numeric(30,10),
  "cci_upper_consec" int4,
  "bands_lower" numeric(30,10),
  "bands_lower_consec" int4,
  "bands_middle" numeric(30,10),
  "bands_middle_consec" int4,
  "bands_upper" numeric(30,10),
  "bands_upper_consec" int4,
  "lon_lonma_diff" numeric(30,10),
  "lon" numeric(30,10),
  "lonma" numeric(30,10),
  "histgram" numeric(30,10),
  "dif" numeric(30,10),
  "dem" numeric(30,10),
  "adx" numeric(30,10),
  "plus_di" numeric(30,10),
  "obv_2" int8,
  "slowk" numeric(30,10),
  "rsi_2" numeric(30,10),
  "cci_neg_90_2" numeric(30,10),
  "cci_pos_90_2" numeric(30,10),
  "lower_band" numeric(30,10),
  "middle_band" numeric(30,10),
  "upper_band" numeric(30,10),
  "lst_close" numeric(30,10),
  "code2" varchar(20) COLLATE "pg_catalog"."default",
  "name2" varchar(50) COLLATE "pg_catalog"."default",
  "zhangdiefu2" numeric(30,10),
  "volume_consec2" numeric(30,10),
  "volume_50_consec2" numeric(30,10)
)
;

-- ----------------------------
-- Table structure for ext_board_daily_snap
-- ----------------------------
DROP TABLE IF EXISTS "public"."ext_board_daily_snap";
CREATE TABLE "public"."ext_board_daily_snap" (
  "stock_code" varchar(10) COLLATE "pg_catalog"."default" NOT NULL,
  "board_id" int8 NOT NULL,
  "date" date NOT NULL,
  "board_rank" int4,
  "weight" numeric(10,6),
  "contribution_score" numeric(20,8)
)
;

-- ----------------------------
-- Table structure for ext_board_heat_daily
-- ----------------------------
DROP TABLE IF EXISTS "public"."ext_board_heat_daily";
CREATE TABLE "public"."ext_board_heat_daily" (
  "trade_date" date NOT NULL,
  "board_id" int8 NOT NULL,
  "stock_count" int4 DEFAULT 0,
  "b1_rank_sum" numeric(20,8) DEFAULT 0,
  "b2_rank_avg" numeric(20,8) DEFAULT 0,
  "c1_score_sum" numeric(20,8) DEFAULT 0,
  "c2_score_avg" numeric(20,8) DEFAULT 0,
  "heat_raw" numeric(20,8) DEFAULT 0,
  "heat_pct" numeric(10,8) DEFAULT 0,
  "needle_density" numeric(10,4),
  "avg_volume" numeric(10,2),
  "created_at" timestamp(6) DEFAULT CURRENT_TIMESTAMP,
  "updated_at" timestamp(6) DEFAULT CURRENT_TIMESTAMP,
  "score_stddev" numeric(10,4)
)
;

-- ----------------------------
-- Table structure for ext_board_list
-- ----------------------------
DROP TABLE IF EXISTS "public"."ext_board_list";
CREATE TABLE "public"."ext_board_list" (
  "id" int8 NOT NULL DEFAULT nextval('ext_board_list_id_seq'::regclass),
  "provider_id" int4 NOT NULL,
  "board_code" varchar(50) COLLATE "pg_catalog"."default" NOT NULL,
  "board_name" varchar(200) COLLATE "pg_catalog"."default" NOT NULL,
  "board_type" varchar(50) COLLATE "pg_catalog"."default",
  "stock_count" int4 DEFAULT 0,
  "is_active" bool DEFAULT true,
  "created_at" timestamp(6) DEFAULT CURRENT_TIMESTAMP,
  "updated_at" timestamp(6) DEFAULT CURRENT_TIMESTAMP,
  "is_broad_index" bool DEFAULT false
)
;

-- ----------------------------
-- Table structure for ext_board_local_map
-- ----------------------------
DROP TABLE IF EXISTS "public"."ext_board_local_map";
CREATE TABLE "public"."ext_board_local_map" (
  "ext_board_id" int8 NOT NULL,
  "local_sector_id" int8 NOT NULL,
  "match_type" varchar(20) COLLATE "pg_catalog"."default" DEFAULT 'auto'::character varying,
  "confidence" numeric(5,2),
  "created_at" timestamp(6) DEFAULT CURRENT_TIMESTAMP,
  "updated_by" varchar(50) COLLATE "pg_catalog"."default"
)
;

-- ----------------------------
-- Table structure for ext_providers
-- ----------------------------
DROP TABLE IF EXISTS "public"."ext_providers";
CREATE TABLE "public"."ext_providers" (
  "id" int4 NOT NULL DEFAULT nextval('ext_providers_id_seq'::regclass),
  "code" varchar(20) COLLATE "pg_catalog"."default" NOT NULL,
  "name" varchar(50) COLLATE "pg_catalog"."default" NOT NULL,
  "description" text COLLATE "pg_catalog"."default",
  "api_source" varchar(100) COLLATE "pg_catalog"."default",
  "is_active" bool DEFAULT true,
  "created_at" timestamp(6) DEFAULT CURRENT_TIMESTAMP
)
;

-- ----------------------------
-- Table structure for operation_logs
-- ----------------------------
DROP TABLE IF EXISTS "public"."operation_logs";
CREATE TABLE "public"."operation_logs" (
  "id" int4 NOT NULL DEFAULT nextval('operation_logs_id_seq'::regclass),
  "log_type" varchar(20) COLLATE "pg_catalog"."default" NOT NULL,
  "action" varchar(50) COLLATE "pg_catalog"."default" NOT NULL,
  "operator_id" int4,
  "operator_name" varchar(50) COLLATE "pg_catalog"."default",
  "target_type" varchar(20) COLLATE "pg_catalog"."default",
  "target_id" int4,
  "target_name" varchar(100) COLLATE "pg_catalog"."default",
  "ip_address" varchar(45) COLLATE "pg_catalog"."default",
  "user_agent" varchar(500) COLLATE "pg_catalog"."default",
  "detail" jsonb,
  "old_value" jsonb,
  "new_value" jsonb,
  "status" varchar(20) COLLATE "pg_catalog"."default" DEFAULT 'success'::character varying,
  "error_message" text COLLATE "pg_catalog"."default",
  "created_at" timestamp(6) DEFAULT CURRENT_TIMESTAMP
)
;

-- ----------------------------
-- Table structure for roles
-- ----------------------------
DROP TABLE IF EXISTS "public"."roles";
CREATE TABLE "public"."roles" (
  "id" int4 NOT NULL DEFAULT nextval('roles_id_seq'::regclass),
  "name" varchar(50) COLLATE "pg_catalog"."default" NOT NULL,
  "display_name" varchar(100) COLLATE "pg_catalog"."default" NOT NULL,
  "description" varchar(255) COLLATE "pg_catalog"."default",
  "permissions" jsonb NOT NULL DEFAULT '[]'::jsonb,
  "is_system" bool DEFAULT false,
  "is_active" bool DEFAULT true,
  "created_at" timestamp(6) DEFAULT CURRENT_TIMESTAMP,
  "updated_at" timestamp(6) DEFAULT CURRENT_TIMESTAMP
)
;

-- ----------------------------
-- Table structure for sectors
-- ----------------------------
DROP TABLE IF EXISTS "public"."sectors";
CREATE TABLE "public"."sectors" (
  "id" int8 NOT NULL DEFAULT nextval('sectors_id_seq'::regclass),
  "sector_name" varchar(100) COLLATE "pg_catalog"."default" NOT NULL
)
;

-- ----------------------------
-- Table structure for stocks
-- ----------------------------
DROP TABLE IF EXISTS "public"."stocks";
CREATE TABLE "public"."stocks" (
  "stock_code" varchar(10) COLLATE "pg_catalog"."default" NOT NULL,
  "stock_name" varchar(50) COLLATE "pg_catalog"."default" NOT NULL,
  "industry" varchar(100) COLLATE "pg_catalog"."default",
  "last_updated" timestamp(6)
)
;

-- ----------------------------
-- Table structure for system_configs
-- ----------------------------
DROP TABLE IF EXISTS "public"."system_configs";
CREATE TABLE "public"."system_configs" (
  "id" int4 NOT NULL DEFAULT nextval('system_configs_id_seq'::regclass),
  "config_key" varchar(100) COLLATE "pg_catalog"."default" NOT NULL,
  "config_value" text COLLATE "pg_catalog"."default" NOT NULL,
  "config_type" varchar(20) COLLATE "pg_catalog"."default" DEFAULT 'string'::character varying,
  "category" varchar(50) COLLATE "pg_catalog"."default" NOT NULL,
  "description" varchar(255) COLLATE "pg_catalog"."default",
  "updated_at" timestamp(6) DEFAULT CURRENT_TIMESTAMP,
  "updated_by" int4
)
;

-- ----------------------------
-- Table structure for user_roles
-- ----------------------------
DROP TABLE IF EXISTS "public"."user_roles";
CREATE TABLE "public"."user_roles" (
  "user_id" int4 NOT NULL,
  "role_id" int4 NOT NULL,
  "created_at" timestamp(6) DEFAULT CURRENT_TIMESTAMP
)
;

-- ----------------------------
-- Table structure for user_sessions
-- ----------------------------
DROP TABLE IF EXISTS "public"."user_sessions";
CREATE TABLE "public"."user_sessions" (
  "id" int4 NOT NULL DEFAULT nextval('user_sessions_id_seq'::regclass),
  "user_id" int4 NOT NULL,
  "device_id" varchar(100) COLLATE "pg_catalog"."default" NOT NULL,
  "device_name" varchar(100) COLLATE "pg_catalog"."default",
  "session_key_encrypted" text COLLATE "pg_catalog"."default" NOT NULL,
  "refresh_token" varchar(500) COLLATE "pg_catalog"."default",
  "created_at" timestamp(6) DEFAULT CURRENT_TIMESTAMP,
  "expires_at" timestamp(6) NOT NULL,
  "last_active" timestamp(6) DEFAULT CURRENT_TIMESTAMP,
  "ip_address" varchar(45) COLLATE "pg_catalog"."default",
  "user_agent" varchar(500) COLLATE "pg_catalog"."default",
  "platform" varchar(50) COLLATE "pg_catalog"."default",
  "app_version" varchar(20) COLLATE "pg_catalog"."default",
  "location" varchar(100) COLLATE "pg_catalog"."default",
  "device_info" jsonb,
  "current_status" varchar(20) COLLATE "pg_catalog"."default" DEFAULT 'online'::character varying,
  "is_revoked" bool DEFAULT false,
  "revoked_at" timestamp(6),
  "revoked_by" int4
)
;
COMMENT ON COLUMN "public"."user_sessions"."device_id" IS '设备唯一标识';
COMMENT ON COLUMN "public"."user_sessions"."session_key_encrypted" IS '会话密钥(用户密钥加密)';
COMMENT ON COLUMN "public"."user_sessions"."refresh_token" IS '刷新令牌';
COMMENT ON TABLE "public"."user_sessions" IS '用户会话表 - 管理多设备登录';

-- ----------------------------
-- Table structure for users
-- ----------------------------
DROP TABLE IF EXISTS "public"."users";
CREATE TABLE "public"."users" (
  "id" int4 NOT NULL DEFAULT nextval('users_id_seq'::regclass),
  "username" varchar(50) COLLATE "pg_catalog"."default" NOT NULL,
  "password_hash" varchar(255) COLLATE "pg_catalog"."default" NOT NULL,
  "user_key_encrypted" text COLLATE "pg_catalog"."default" NOT NULL,
  "role" varchar(20) COLLATE "pg_catalog"."default" DEFAULT 'user'::character varying,
  "is_active" bool DEFAULT true,
  "created_at" timestamp(6) DEFAULT CURRENT_TIMESTAMP,
  "last_login" timestamp(6),
  "allowed_devices" int4 DEFAULT 3,
  "offline_enabled" bool DEFAULT true,
  "offline_days" int4 DEFAULT 7,
  "email" varchar(255) COLLATE "pg_catalog"."default",
  "phone" varchar(20) COLLATE "pg_catalog"."default",
  "nickname" varchar(50) COLLATE "pg_catalog"."default",
  "avatar_url" varchar(500) COLLATE "pg_catalog"."default",
  "remark" text COLLATE "pg_catalog"."default",
  "expires_at" timestamp(6),
  "failed_attempts" int4 DEFAULT 0,
  "locked_until" timestamp(6),
  "password_changed_at" timestamp(6),
  "created_by" int4,
  "updated_at" timestamp(6) DEFAULT CURRENT_TIMESTAMP,
  "deleted_at" timestamp(6),
  "token_version" int4 DEFAULT 1
)
;
COMMENT ON COLUMN "public"."users"."username" IS '用户名，唯一';
COMMENT ON COLUMN "public"."users"."password_hash" IS '密码哈希(bcrypt)';
COMMENT ON COLUMN "public"."users"."user_key_encrypted" IS '用户密钥(主密钥加密)';
COMMENT ON COLUMN "public"."users"."role" IS '角色: admin/user';
COMMENT ON COLUMN "public"."users"."is_active" IS '是否启用';
COMMENT ON COLUMN "public"."users"."allowed_devices" IS '允许同时登录设备数';
COMMENT ON COLUMN "public"."users"."offline_enabled" IS '是否允许离线使用';
COMMENT ON COLUMN "public"."users"."offline_days" IS '离线数据保留天数';
COMMENT ON TABLE "public"."users" IS '用户表 - 存储用户认证信息';

-- ----------------------------
-- Function structure for gin_extract_query_trgm
-- ----------------------------
DROP FUNCTION IF EXISTS "public"."gin_extract_query_trgm"(text, internal, int2, internal, internal, internal, internal);
CREATE OR REPLACE FUNCTION "public"."gin_extract_query_trgm"(text, internal, int2, internal, internal, internal, internal)
  RETURNS "pg_catalog"."internal" AS '$libdir/pg_trgm', 'gin_extract_query_trgm'
  LANGUAGE c IMMUTABLE STRICT
  COST 1;

-- ----------------------------
-- Function structure for gin_extract_value_trgm
-- ----------------------------
DROP FUNCTION IF EXISTS "public"."gin_extract_value_trgm"(text, internal);
CREATE OR REPLACE FUNCTION "public"."gin_extract_value_trgm"(text, internal)
  RETURNS "pg_catalog"."internal" AS '$libdir/pg_trgm', 'gin_extract_value_trgm'
  LANGUAGE c IMMUTABLE STRICT
  COST 1;

-- ----------------------------
-- Function structure for gin_trgm_consistent
-- ----------------------------
DROP FUNCTION IF EXISTS "public"."gin_trgm_consistent"(internal, int2, text, int4, internal, internal, internal, internal);
CREATE OR REPLACE FUNCTION "public"."gin_trgm_consistent"(internal, int2, text, int4, internal, internal, internal, internal)
  RETURNS "pg_catalog"."bool" AS '$libdir/pg_trgm', 'gin_trgm_consistent'
  LANGUAGE c IMMUTABLE STRICT
  COST 1;

-- ----------------------------
-- Function structure for gin_trgm_triconsistent
-- ----------------------------
DROP FUNCTION IF EXISTS "public"."gin_trgm_triconsistent"(internal, int2, text, int4, internal, internal, internal);
CREATE OR REPLACE FUNCTION "public"."gin_trgm_triconsistent"(internal, int2, text, int4, internal, internal, internal)
  RETURNS "pg_catalog"."char" AS '$libdir/pg_trgm', 'gin_trgm_triconsistent'
  LANGUAGE c IMMUTABLE STRICT
  COST 1;

-- ----------------------------
-- Function structure for gtrgm_compress
-- ----------------------------
DROP FUNCTION IF EXISTS "public"."gtrgm_compress"(internal);
CREATE OR REPLACE FUNCTION "public"."gtrgm_compress"(internal)
  RETURNS "pg_catalog"."internal" AS '$libdir/pg_trgm', 'gtrgm_compress'
  LANGUAGE c IMMUTABLE STRICT
  COST 1;

-- ----------------------------
-- Function structure for gtrgm_consistent
-- ----------------------------
DROP FUNCTION IF EXISTS "public"."gtrgm_consistent"(internal, text, int2, oid, internal);
CREATE OR REPLACE FUNCTION "public"."gtrgm_consistent"(internal, text, int2, oid, internal)
  RETURNS "pg_catalog"."bool" AS '$libdir/pg_trgm', 'gtrgm_consistent'
  LANGUAGE c IMMUTABLE STRICT
  COST 1;

-- ----------------------------
-- Function structure for gtrgm_decompress
-- ----------------------------
DROP FUNCTION IF EXISTS "public"."gtrgm_decompress"(internal);
CREATE OR REPLACE FUNCTION "public"."gtrgm_decompress"(internal)
  RETURNS "pg_catalog"."internal" AS '$libdir/pg_trgm', 'gtrgm_decompress'
  LANGUAGE c IMMUTABLE STRICT
  COST 1;

-- ----------------------------
-- Function structure for gtrgm_distance
-- ----------------------------
DROP FUNCTION IF EXISTS "public"."gtrgm_distance"(internal, text, int2, oid, internal);
CREATE OR REPLACE FUNCTION "public"."gtrgm_distance"(internal, text, int2, oid, internal)
  RETURNS "pg_catalog"."float8" AS '$libdir/pg_trgm', 'gtrgm_distance'
  LANGUAGE c IMMUTABLE STRICT
  COST 1;

-- ----------------------------
-- Function structure for gtrgm_in
-- ----------------------------
DROP FUNCTION IF EXISTS "public"."gtrgm_in"(cstring);
CREATE OR REPLACE FUNCTION "public"."gtrgm_in"(cstring)
  RETURNS "public"."gtrgm" AS '$libdir/pg_trgm', 'gtrgm_in'
  LANGUAGE c IMMUTABLE STRICT
  COST 1;

-- ----------------------------
-- Function structure for gtrgm_options
-- ----------------------------
DROP FUNCTION IF EXISTS "public"."gtrgm_options"(internal);
CREATE OR REPLACE FUNCTION "public"."gtrgm_options"(internal)
  RETURNS "pg_catalog"."void" AS '$libdir/pg_trgm', 'gtrgm_options'
  LANGUAGE c IMMUTABLE
  COST 1;

-- ----------------------------
-- Function structure for gtrgm_out
-- ----------------------------
DROP FUNCTION IF EXISTS "public"."gtrgm_out"("public"."gtrgm");
CREATE OR REPLACE FUNCTION "public"."gtrgm_out"("public"."gtrgm")
  RETURNS "pg_catalog"."cstring" AS '$libdir/pg_trgm', 'gtrgm_out'
  LANGUAGE c IMMUTABLE STRICT
  COST 1;

-- ----------------------------
-- Function structure for gtrgm_penalty
-- ----------------------------
DROP FUNCTION IF EXISTS "public"."gtrgm_penalty"(internal, internal, internal);
CREATE OR REPLACE FUNCTION "public"."gtrgm_penalty"(internal, internal, internal)
  RETURNS "pg_catalog"."internal" AS '$libdir/pg_trgm', 'gtrgm_penalty'
  LANGUAGE c IMMUTABLE STRICT
  COST 1;

-- ----------------------------
-- Function structure for gtrgm_picksplit
-- ----------------------------
DROP FUNCTION IF EXISTS "public"."gtrgm_picksplit"(internal, internal);
CREATE OR REPLACE FUNCTION "public"."gtrgm_picksplit"(internal, internal)
  RETURNS "pg_catalog"."internal" AS '$libdir/pg_trgm', 'gtrgm_picksplit'
  LANGUAGE c IMMUTABLE STRICT
  COST 1;

-- ----------------------------
-- Function structure for gtrgm_same
-- ----------------------------
DROP FUNCTION IF EXISTS "public"."gtrgm_same"("public"."gtrgm", "public"."gtrgm", internal);
CREATE OR REPLACE FUNCTION "public"."gtrgm_same"("public"."gtrgm", "public"."gtrgm", internal)
  RETURNS "pg_catalog"."internal" AS '$libdir/pg_trgm', 'gtrgm_same'
  LANGUAGE c IMMUTABLE STRICT
  COST 1;

-- ----------------------------
-- Function structure for gtrgm_union
-- ----------------------------
DROP FUNCTION IF EXISTS "public"."gtrgm_union"(internal, internal);
CREATE OR REPLACE FUNCTION "public"."gtrgm_union"(internal, internal)
  RETURNS "public"."gtrgm" AS '$libdir/pg_trgm', 'gtrgm_union'
  LANGUAGE c IMMUTABLE STRICT
  COST 1;

-- ----------------------------
-- Function structure for set_limit
-- ----------------------------
DROP FUNCTION IF EXISTS "public"."set_limit"(float4);
CREATE OR REPLACE FUNCTION "public"."set_limit"(float4)
  RETURNS "pg_catalog"."float4" AS '$libdir/pg_trgm', 'set_limit'
  LANGUAGE c VOLATILE STRICT
  COST 1;

-- ----------------------------
-- Function structure for show_limit
-- ----------------------------
DROP FUNCTION IF EXISTS "public"."show_limit"();
CREATE OR REPLACE FUNCTION "public"."show_limit"()
  RETURNS "pg_catalog"."float4" AS '$libdir/pg_trgm', 'show_limit'
  LANGUAGE c STABLE STRICT
  COST 1;

-- ----------------------------
-- Function structure for show_trgm
-- ----------------------------
DROP FUNCTION IF EXISTS "public"."show_trgm"(text);
CREATE OR REPLACE FUNCTION "public"."show_trgm"(text)
  RETURNS "pg_catalog"."_text" AS '$libdir/pg_trgm', 'show_trgm'
  LANGUAGE c IMMUTABLE STRICT
  COST 1;

-- ----------------------------
-- Function structure for similarity
-- ----------------------------
DROP FUNCTION IF EXISTS "public"."similarity"(text, text);
CREATE OR REPLACE FUNCTION "public"."similarity"(text, text)
  RETURNS "pg_catalog"."float4" AS '$libdir/pg_trgm', 'similarity'
  LANGUAGE c IMMUTABLE STRICT
  COST 1;

-- ----------------------------
-- Function structure for similarity_dist
-- ----------------------------
DROP FUNCTION IF EXISTS "public"."similarity_dist"(text, text);
CREATE OR REPLACE FUNCTION "public"."similarity_dist"(text, text)
  RETURNS "pg_catalog"."float4" AS '$libdir/pg_trgm', 'similarity_dist'
  LANGUAGE c IMMUTABLE STRICT
  COST 1;

-- ----------------------------
-- Function structure for similarity_op
-- ----------------------------
DROP FUNCTION IF EXISTS "public"."similarity_op"(text, text);
CREATE OR REPLACE FUNCTION "public"."similarity_op"(text, text)
  RETURNS "pg_catalog"."bool" AS '$libdir/pg_trgm', 'similarity_op'
  LANGUAGE c STABLE STRICT
  COST 1;

-- ----------------------------
-- Function structure for strict_word_similarity
-- ----------------------------
DROP FUNCTION IF EXISTS "public"."strict_word_similarity"(text, text);
CREATE OR REPLACE FUNCTION "public"."strict_word_similarity"(text, text)
  RETURNS "pg_catalog"."float4" AS '$libdir/pg_trgm', 'strict_word_similarity'
  LANGUAGE c IMMUTABLE STRICT
  COST 1;

-- ----------------------------
-- Function structure for strict_word_similarity_commutator_op
-- ----------------------------
DROP FUNCTION IF EXISTS "public"."strict_word_similarity_commutator_op"(text, text);
CREATE OR REPLACE FUNCTION "public"."strict_word_similarity_commutator_op"(text, text)
  RETURNS "pg_catalog"."bool" AS '$libdir/pg_trgm', 'strict_word_similarity_commutator_op'
  LANGUAGE c STABLE STRICT
  COST 1;

-- ----------------------------
-- Function structure for strict_word_similarity_dist_commutator_op
-- ----------------------------
DROP FUNCTION IF EXISTS "public"."strict_word_similarity_dist_commutator_op"(text, text);
CREATE OR REPLACE FUNCTION "public"."strict_word_similarity_dist_commutator_op"(text, text)
  RETURNS "pg_catalog"."float4" AS '$libdir/pg_trgm', 'strict_word_similarity_dist_commutator_op'
  LANGUAGE c IMMUTABLE STRICT
  COST 1;

-- ----------------------------
-- Function structure for strict_word_similarity_dist_op
-- ----------------------------
DROP FUNCTION IF EXISTS "public"."strict_word_similarity_dist_op"(text, text);
CREATE OR REPLACE FUNCTION "public"."strict_word_similarity_dist_op"(text, text)
  RETURNS "pg_catalog"."float4" AS '$libdir/pg_trgm', 'strict_word_similarity_dist_op'
  LANGUAGE c IMMUTABLE STRICT
  COST 1;

-- ----------------------------
-- Function structure for strict_word_similarity_op
-- ----------------------------
DROP FUNCTION IF EXISTS "public"."strict_word_similarity_op"(text, text);
CREATE OR REPLACE FUNCTION "public"."strict_word_similarity_op"(text, text)
  RETURNS "pg_catalog"."bool" AS '$libdir/pg_trgm', 'strict_word_similarity_op'
  LANGUAGE c STABLE STRICT
  COST 1;

-- ----------------------------
-- Function structure for word_similarity
-- ----------------------------
DROP FUNCTION IF EXISTS "public"."word_similarity"(text, text);
CREATE OR REPLACE FUNCTION "public"."word_similarity"(text, text)
  RETURNS "pg_catalog"."float4" AS '$libdir/pg_trgm', 'word_similarity'
  LANGUAGE c IMMUTABLE STRICT
  COST 1;

-- ----------------------------
-- Function structure for word_similarity_commutator_op
-- ----------------------------
DROP FUNCTION IF EXISTS "public"."word_similarity_commutator_op"(text, text);
CREATE OR REPLACE FUNCTION "public"."word_similarity_commutator_op"(text, text)
  RETURNS "pg_catalog"."bool" AS '$libdir/pg_trgm', 'word_similarity_commutator_op'
  LANGUAGE c STABLE STRICT
  COST 1;

-- ----------------------------
-- Function structure for word_similarity_dist_commutator_op
-- ----------------------------
DROP FUNCTION IF EXISTS "public"."word_similarity_dist_commutator_op"(text, text);
CREATE OR REPLACE FUNCTION "public"."word_similarity_dist_commutator_op"(text, text)
  RETURNS "pg_catalog"."float4" AS '$libdir/pg_trgm', 'word_similarity_dist_commutator_op'
  LANGUAGE c IMMUTABLE STRICT
  COST 1;

-- ----------------------------
-- Function structure for word_similarity_dist_op
-- ----------------------------
DROP FUNCTION IF EXISTS "public"."word_similarity_dist_op"(text, text);
CREATE OR REPLACE FUNCTION "public"."word_similarity_dist_op"(text, text)
  RETURNS "pg_catalog"."float4" AS '$libdir/pg_trgm', 'word_similarity_dist_op'
  LANGUAGE c IMMUTABLE STRICT
  COST 1;

-- ----------------------------
-- Function structure for word_similarity_op
-- ----------------------------
DROP FUNCTION IF EXISTS "public"."word_similarity_op"(text, text);
CREATE OR REPLACE FUNCTION "public"."word_similarity_op"(text, text)
  RETURNS "pg_catalog"."bool" AS '$libdir/pg_trgm', 'word_similarity_op'
  LANGUAGE c STABLE STRICT
  COST 1;

-- ----------------------------
-- View structure for v_ext_board_full
-- ----------------------------
DROP VIEW IF EXISTS "public"."v_ext_board_full";
CREATE VIEW "public"."v_ext_board_full" AS  SELECT b.id,
    b.board_code,
    b.board_name,
    b.board_type,
    b.stock_count,
    b.is_active,
    b.updated_at,
    p.code AS provider_code,
    p.name AS provider_name
   FROM ext_board_list b
     JOIN ext_providers p ON p.id = b.provider_id;

-- ----------------------------
-- View structure for v_ext_board_stocks_latest
-- ----------------------------
DROP VIEW IF EXISTS "public"."v_ext_board_stocks_latest";
CREATE VIEW "public"."v_ext_board_stocks_latest" AS  SELECT b.board_name,
    b.board_type,
    p.code AS provider_code,
    s.stock_code,
    s.stock_name,
    s.industry,
    snap.board_rank,
    snap.date
   FROM ext_board_daily_snap snap
     JOIN ext_board_list b ON b.id = snap.board_id
     JOIN ext_providers p ON p.id = b.provider_id
     JOIN stocks s ON s.stock_code::text = snap.stock_code::text
  WHERE snap.date = (( SELECT max(ext_board_daily_snap.date) AS max
           FROM ext_board_daily_snap));

-- ----------------------------
-- View structure for v_ext_board_mapping
-- ----------------------------
DROP VIEW IF EXISTS "public"."v_ext_board_mapping";
CREATE VIEW "public"."v_ext_board_mapping" AS  SELECT b.board_name AS ext_board_name,
    b.board_code AS ext_board_code,
    p.code AS provider_code,
    sec.sector_name AS local_sector_name,
    m.match_type,
    m.confidence
   FROM ext_board_local_map m
     JOIN ext_board_list b ON b.id = m.ext_board_id
     JOIN ext_providers p ON p.id = b.provider_id
     JOIN sectors sec ON sec.id = m.local_sector_id;

-- ----------------------------
-- Alter sequences owned by
-- ----------------------------
ALTER SEQUENCE "public"."board_blacklist_id_seq"
OWNED BY "public"."board_blacklist"."id";
SELECT setval('"public"."board_blacklist_id_seq"', 30, true);

-- ----------------------------
-- Alter sequences owned by
-- ----------------------------
ALTER SEQUENCE "public"."daily_sector_data_id_seq"
OWNED BY "public"."daily_sector_data"."id";
SELECT setval('"public"."daily_sector_data_id_seq"', 28205, true);

-- ----------------------------
-- Alter sequences owned by
-- ----------------------------
ALTER SEQUENCE "public"."daily_stock_data_id_seq"
OWNED BY "public"."daily_stock_data"."id";
SELECT setval('"public"."daily_stock_data_id_seq"', 296253, true);

-- ----------------------------
-- Alter sequences owned by
-- ----------------------------
ALTER SEQUENCE "public"."ext_board_list_id_seq"
OWNED BY "public"."ext_board_list"."id";
SELECT setval('"public"."ext_board_list_id_seq"', 9294, true);

-- ----------------------------
-- Alter sequences owned by
-- ----------------------------
ALTER SEQUENCE "public"."ext_providers_id_seq"
OWNED BY "public"."ext_providers"."id";
SELECT setval('"public"."ext_providers_id_seq"', 2, true);

-- ----------------------------
-- Alter sequences owned by
-- ----------------------------
ALTER SEQUENCE "public"."operation_logs_id_seq"
OWNED BY "public"."operation_logs"."id";
SELECT setval('"public"."operation_logs_id_seq"', 2, true);

-- ----------------------------
-- Alter sequences owned by
-- ----------------------------
ALTER SEQUENCE "public"."roles_id_seq"
OWNED BY "public"."roles"."id";
SELECT setval('"public"."roles_id_seq"', 4, true);

-- ----------------------------
-- Alter sequences owned by
-- ----------------------------
ALTER SEQUENCE "public"."sectors_id_seq"
OWNED BY "public"."sectors"."id";
SELECT setval('"public"."sectors_id_seq"', 571, true);

-- ----------------------------
-- Alter sequences owned by
-- ----------------------------
ALTER SEQUENCE "public"."system_configs_id_seq"
OWNED BY "public"."system_configs"."id";
SELECT setval('"public"."system_configs_id_seq"', 33, true);

-- ----------------------------
-- Alter sequences owned by
-- ----------------------------
ALTER SEQUENCE "public"."user_sessions_id_seq"
OWNED BY "public"."user_sessions"."id";
SELECT setval('"public"."user_sessions_id_seq"', 11, true);

-- ----------------------------
-- Alter sequences owned by
-- ----------------------------
ALTER SEQUENCE "public"."users_id_seq"
OWNED BY "public"."users"."id";
SELECT setval('"public"."users_id_seq"', 2, true);

-- ----------------------------
-- Uniques structure for table board_blacklist
-- ----------------------------
ALTER TABLE "public"."board_blacklist" ADD CONSTRAINT "board_blacklist_keyword_key" UNIQUE ("keyword");

-- ----------------------------
-- Primary Key structure for table board_blacklist
-- ----------------------------
ALTER TABLE "public"."board_blacklist" ADD CONSTRAINT "board_blacklist_pkey" PRIMARY KEY ("id");

-- ----------------------------
-- Indexes structure for table cache_stock_board_signal
-- ----------------------------
CREATE INDEX "idx_cache_driver_board" ON "public"."cache_stock_board_signal" USING btree (
  "trade_date" "pg_catalog"."date_ops" ASC NULLS LAST,
  "max_driver_board_id" "pg_catalog"."int8_ops" ASC NULLS LAST
);
CREATE INDEX "idx_cache_final_score" ON "public"."cache_stock_board_signal" USING btree (
  "trade_date" "pg_catalog"."date_ops" ASC NULLS LAST,
  "final_score" "pg_catalog"."numeric_ops" DESC NULLS FIRST
);
CREATE INDEX "idx_cache_market_rank" ON "public"."cache_stock_board_signal" USING btree (
  "trade_date" "pg_catalog"."date_ops" ASC NULLS LAST,
  "market_rank" "pg_catalog"."int4_ops" ASC NULLS LAST
);
CREATE INDEX "idx_cache_signal_level" ON "public"."cache_stock_board_signal" USING btree (
  "trade_date" "pg_catalog"."date_ops" ASC NULLS LAST,
  "signal_level" COLLATE "pg_catalog"."default" "pg_catalog"."text_ops" ASC NULLS LAST
);

-- ----------------------------
-- Primary Key structure for table cache_stock_board_signal
-- ----------------------------
ALTER TABLE "public"."cache_stock_board_signal" ADD CONSTRAINT "cache_stock_board_signal_pkey" PRIMARY KEY ("trade_date", "stock_code");

-- ----------------------------
-- Indexes structure for table daily_sector_data
-- ----------------------------
CREATE INDEX "idx_daily_sector_date_rank" ON "public"."daily_sector_data" USING btree (
  "date" "pg_catalog"."date_ops" ASC NULLS LAST,
  "rank" "pg_catalog"."int4_ops" ASC NULLS LAST
);
CREATE UNIQUE INDEX "idx_daily_sector_date_unique" ON "public"."daily_sector_data" USING btree (
  "sector_id" "pg_catalog"."int8_ops" ASC NULLS LAST,
  "date" "pg_catalog"."date_ops" ASC NULLS LAST
);

-- ----------------------------
-- Primary Key structure for table daily_sector_data
-- ----------------------------
ALTER TABLE "public"."daily_sector_data" ADD CONSTRAINT "daily_sector_data_pkey" PRIMARY KEY ("id");

-- ----------------------------
-- Indexes structure for table daily_stock_data
-- ----------------------------
CREATE INDEX "idx_daily_date_rank" ON "public"."daily_stock_data" USING btree (
  "date" "pg_catalog"."date_ops" ASC NULLS LAST,
  "rank" "pg_catalog"."int4_ops" ASC NULLS LAST
);
CREATE UNIQUE INDEX "idx_daily_stock_date_unique" ON "public"."daily_stock_data" USING btree (
  "stock_code" COLLATE "pg_catalog"."default" "pg_catalog"."text_ops" ASC NULLS LAST,
  "date" "pg_catalog"."date_ops" ASC NULLS LAST
);

-- ----------------------------
-- Primary Key structure for table daily_stock_data
-- ----------------------------
ALTER TABLE "public"."daily_stock_data" ADD CONSTRAINT "daily_stock_data_pkey" PRIMARY KEY ("id");

-- ----------------------------
-- Indexes structure for table ext_board_daily_snap
-- ----------------------------
CREATE INDEX "idx_ext_daily_date" ON "public"."ext_board_daily_snap" USING btree (
  "date" "pg_catalog"."date_ops" ASC NULLS LAST
);
CREATE INDEX "idx_ext_daily_query" ON "public"."ext_board_daily_snap" USING btree (
  "board_id" "pg_catalog"."int8_ops" ASC NULLS LAST,
  "date" "pg_catalog"."date_ops" ASC NULLS LAST
);
CREATE INDEX "idx_ext_daily_stock_history" ON "public"."ext_board_daily_snap" USING btree (
  "stock_code" COLLATE "pg_catalog"."default" "pg_catalog"."text_ops" ASC NULLS LAST,
  "date" "pg_catalog"."date_ops" ASC NULLS LAST
);
CREATE INDEX "idx_snap_contrib" ON "public"."ext_board_daily_snap" USING btree (
  "board_id" "pg_catalog"."int8_ops" ASC NULLS LAST,
  "date" "pg_catalog"."date_ops" ASC NULLS LAST,
  "contribution_score" "pg_catalog"."numeric_ops" DESC NULLS FIRST
);

-- ----------------------------
-- Primary Key structure for table ext_board_daily_snap
-- ----------------------------
ALTER TABLE "public"."ext_board_daily_snap" ADD CONSTRAINT "ext_board_daily_snap_pkey" PRIMARY KEY ("stock_code", "board_id", "date");

-- ----------------------------
-- Indexes structure for table ext_board_heat_daily
-- ----------------------------
CREATE INDEX "idx_ext_heat_board" ON "public"."ext_board_heat_daily" USING btree (
  "board_id" "pg_catalog"."int8_ops" ASC NULLS LAST
);
CREATE INDEX "idx_ext_heat_date" ON "public"."ext_board_heat_daily" USING btree (
  "trade_date" "pg_catalog"."date_ops" ASC NULLS LAST
);
CREATE INDEX "idx_ext_heat_pct" ON "public"."ext_board_heat_daily" USING btree (
  "trade_date" "pg_catalog"."date_ops" ASC NULLS LAST,
  "heat_pct" "pg_catalog"."numeric_ops" DESC NULLS FIRST
);

-- ----------------------------
-- Primary Key structure for table ext_board_heat_daily
-- ----------------------------
ALTER TABLE "public"."ext_board_heat_daily" ADD CONSTRAINT "ext_board_heat_daily_pkey" PRIMARY KEY ("trade_date", "board_id");

-- ----------------------------
-- Indexes structure for table ext_board_list
-- ----------------------------
CREATE INDEX "idx_ext_board_name_trgm" ON "public"."ext_board_list" USING gin (
  "board_name" COLLATE "pg_catalog"."default" "public"."gin_trgm_ops"
);
CREATE INDEX "idx_ext_board_provider" ON "public"."ext_board_list" USING btree (
  "provider_id" "pg_catalog"."int4_ops" ASC NULLS LAST
);
CREATE INDEX "idx_ext_board_type" ON "public"."ext_board_list" USING btree (
  "board_type" COLLATE "pg_catalog"."default" "pg_catalog"."text_ops" ASC NULLS LAST
);
CREATE INDEX "idx_ext_board_updated" ON "public"."ext_board_list" USING btree (
  "updated_at" "pg_catalog"."timestamp_ops" ASC NULLS LAST
);

-- ----------------------------
-- Uniques structure for table ext_board_list
-- ----------------------------
ALTER TABLE "public"."ext_board_list" ADD CONSTRAINT "uq_ext_board_source_code" UNIQUE ("provider_id", "board_code");

-- ----------------------------
-- Primary Key structure for table ext_board_list
-- ----------------------------
ALTER TABLE "public"."ext_board_list" ADD CONSTRAINT "ext_board_list_pkey" PRIMARY KEY ("id");

-- ----------------------------
-- Indexes structure for table ext_board_local_map
-- ----------------------------
CREATE INDEX "idx_ext_map_ext_board" ON "public"."ext_board_local_map" USING btree (
  "ext_board_id" "pg_catalog"."int8_ops" ASC NULLS LAST
);
CREATE INDEX "idx_ext_map_local_sector" ON "public"."ext_board_local_map" USING btree (
  "local_sector_id" "pg_catalog"."int8_ops" ASC NULLS LAST
);

-- ----------------------------
-- Primary Key structure for table ext_board_local_map
-- ----------------------------
ALTER TABLE "public"."ext_board_local_map" ADD CONSTRAINT "ext_board_local_map_pkey" PRIMARY KEY ("ext_board_id", "local_sector_id");

-- ----------------------------
-- Uniques structure for table ext_providers
-- ----------------------------
ALTER TABLE "public"."ext_providers" ADD CONSTRAINT "ext_providers_code_key" UNIQUE ("code");

-- ----------------------------
-- Primary Key structure for table ext_providers
-- ----------------------------
ALTER TABLE "public"."ext_providers" ADD CONSTRAINT "ext_providers_pkey" PRIMARY KEY ("id");

-- ----------------------------
-- Indexes structure for table operation_logs
-- ----------------------------
CREATE INDEX "idx_logs_action" ON "public"."operation_logs" USING btree (
  "action" COLLATE "pg_catalog"."default" "pg_catalog"."text_ops" ASC NULLS LAST
);
CREATE INDEX "idx_logs_created_at" ON "public"."operation_logs" USING btree (
  "created_at" "pg_catalog"."timestamp_ops" ASC NULLS LAST
);
CREATE INDEX "idx_logs_log_type" ON "public"."operation_logs" USING btree (
  "log_type" COLLATE "pg_catalog"."default" "pg_catalog"."text_ops" ASC NULLS LAST
);
CREATE INDEX "idx_logs_operator_id" ON "public"."operation_logs" USING btree (
  "operator_id" "pg_catalog"."int4_ops" ASC NULLS LAST
);
CREATE INDEX "idx_logs_status" ON "public"."operation_logs" USING btree (
  "status" COLLATE "pg_catalog"."default" "pg_catalog"."text_ops" ASC NULLS LAST
);
CREATE INDEX "idx_logs_target" ON "public"."operation_logs" USING btree (
  "target_type" COLLATE "pg_catalog"."default" "pg_catalog"."text_ops" ASC NULLS LAST,
  "target_id" "pg_catalog"."int4_ops" ASC NULLS LAST
);

-- ----------------------------
-- Primary Key structure for table operation_logs
-- ----------------------------
ALTER TABLE "public"."operation_logs" ADD CONSTRAINT "operation_logs_pkey" PRIMARY KEY ("id");

-- ----------------------------
-- Indexes structure for table roles
-- ----------------------------
CREATE INDEX "idx_roles_is_active" ON "public"."roles" USING btree (
  "is_active" "pg_catalog"."bool_ops" ASC NULLS LAST
);
CREATE INDEX "idx_roles_name" ON "public"."roles" USING btree (
  "name" COLLATE "pg_catalog"."default" "pg_catalog"."text_ops" ASC NULLS LAST
);

-- ----------------------------
-- Uniques structure for table roles
-- ----------------------------
ALTER TABLE "public"."roles" ADD CONSTRAINT "roles_name_key" UNIQUE ("name");

-- ----------------------------
-- Primary Key structure for table roles
-- ----------------------------
ALTER TABLE "public"."roles" ADD CONSTRAINT "roles_pkey" PRIMARY KEY ("id");

-- ----------------------------
-- Indexes structure for table sectors
-- ----------------------------
CREATE INDEX "idx_sectors_name_trgm" ON "public"."sectors" USING gin (
  "sector_name" COLLATE "pg_catalog"."default" "public"."gin_trgm_ops"
);

-- ----------------------------
-- Uniques structure for table sectors
-- ----------------------------
ALTER TABLE "public"."sectors" ADD CONSTRAINT "uq_sector_name" UNIQUE ("sector_name");

-- ----------------------------
-- Primary Key structure for table sectors
-- ----------------------------
ALTER TABLE "public"."sectors" ADD CONSTRAINT "sectors_pkey" PRIMARY KEY ("id");

-- ----------------------------
-- Indexes structure for table stocks
-- ----------------------------
CREATE INDEX "idx_stocks_code_trgm" ON "public"."stocks" USING gin (
  "stock_code" COLLATE "pg_catalog"."default" "public"."gin_trgm_ops"
);
CREATE INDEX "idx_stocks_name_trgm" ON "public"."stocks" USING gin (
  "stock_name" COLLATE "pg_catalog"."default" "public"."gin_trgm_ops"
);

-- ----------------------------
-- Primary Key structure for table stocks
-- ----------------------------
ALTER TABLE "public"."stocks" ADD CONSTRAINT "stocks_pkey" PRIMARY KEY ("stock_code");

-- ----------------------------
-- Uniques structure for table system_configs
-- ----------------------------
ALTER TABLE "public"."system_configs" ADD CONSTRAINT "system_configs_config_key_key" UNIQUE ("config_key");

-- ----------------------------
-- Primary Key structure for table system_configs
-- ----------------------------
ALTER TABLE "public"."system_configs" ADD CONSTRAINT "system_configs_pkey" PRIMARY KEY ("id");

-- ----------------------------
-- Indexes structure for table user_roles
-- ----------------------------
CREATE INDEX "idx_user_roles_role_id" ON "public"."user_roles" USING btree (
  "role_id" "pg_catalog"."int4_ops" ASC NULLS LAST
);
CREATE INDEX "idx_user_roles_user_id" ON "public"."user_roles" USING btree (
  "user_id" "pg_catalog"."int4_ops" ASC NULLS LAST
);

-- ----------------------------
-- Primary Key structure for table user_roles
-- ----------------------------
ALTER TABLE "public"."user_roles" ADD CONSTRAINT "user_roles_pkey" PRIMARY KEY ("user_id", "role_id");

-- ----------------------------
-- Indexes structure for table user_sessions
-- ----------------------------
CREATE INDEX "idx_sessions_current_status" ON "public"."user_sessions" USING btree (
  "current_status" COLLATE "pg_catalog"."default" "pg_catalog"."text_ops" ASC NULLS LAST
);
CREATE INDEX "idx_sessions_expires" ON "public"."user_sessions" USING btree (
  "expires_at" "pg_catalog"."timestamp_ops" ASC NULLS LAST
);
CREATE INDEX "idx_sessions_expires_at" ON "public"."user_sessions" USING btree (
  "expires_at" "pg_catalog"."timestamp_ops" ASC NULLS LAST
);
CREATE INDEX "idx_sessions_is_revoked" ON "public"."user_sessions" USING btree (
  "is_revoked" "pg_catalog"."bool_ops" ASC NULLS LAST
);
CREATE INDEX "idx_sessions_last_active" ON "public"."user_sessions" USING btree (
  "last_active" "pg_catalog"."timestamp_ops" ASC NULLS LAST
);
CREATE INDEX "idx_sessions_user" ON "public"."user_sessions" USING btree (
  "user_id" "pg_catalog"."int4_ops" ASC NULLS LAST
);

-- ----------------------------
-- Uniques structure for table user_sessions
-- ----------------------------
ALTER TABLE "public"."user_sessions" ADD CONSTRAINT "user_sessions_user_id_device_id_key" UNIQUE ("user_id", "device_id");

-- ----------------------------
-- Primary Key structure for table user_sessions
-- ----------------------------
ALTER TABLE "public"."user_sessions" ADD CONSTRAINT "user_sessions_pkey" PRIMARY KEY ("id");

-- ----------------------------
-- Indexes structure for table users
-- ----------------------------
CREATE INDEX "idx_users_deleted_at" ON "public"."users" USING btree (
  "deleted_at" "pg_catalog"."timestamp_ops" ASC NULLS LAST
);
CREATE INDEX "idx_users_email" ON "public"."users" USING btree (
  "email" COLLATE "pg_catalog"."default" "pg_catalog"."text_ops" ASC NULLS LAST
);
CREATE INDEX "idx_users_is_active" ON "public"."users" USING btree (
  "is_active" "pg_catalog"."bool_ops" ASC NULLS LAST
);
CREATE INDEX "idx_users_role" ON "public"."users" USING btree (
  "role" COLLATE "pg_catalog"."default" "pg_catalog"."text_ops" ASC NULLS LAST
);
CREATE INDEX "idx_users_username" ON "public"."users" USING btree (
  "username" COLLATE "pg_catalog"."default" "pg_catalog"."text_ops" ASC NULLS LAST
);

-- ----------------------------
-- Uniques structure for table users
-- ----------------------------
ALTER TABLE "public"."users" ADD CONSTRAINT "users_username_key" UNIQUE ("username");

-- ----------------------------
-- Primary Key structure for table users
-- ----------------------------
ALTER TABLE "public"."users" ADD CONSTRAINT "users_pkey" PRIMARY KEY ("id");

-- ----------------------------
-- Foreign Keys structure for table daily_sector_data
-- ----------------------------
ALTER TABLE "public"."daily_sector_data" ADD CONSTRAINT "daily_sector_data_sector_id_fkey" FOREIGN KEY ("sector_id") REFERENCES "public"."sectors" ("id") ON DELETE CASCADE ON UPDATE NO ACTION;

-- ----------------------------
-- Foreign Keys structure for table daily_stock_data
-- ----------------------------
ALTER TABLE "public"."daily_stock_data" ADD CONSTRAINT "daily_stock_data_stock_code_fkey" FOREIGN KEY ("stock_code") REFERENCES "public"."stocks" ("stock_code") ON DELETE CASCADE ON UPDATE NO ACTION;

-- ----------------------------
-- Foreign Keys structure for table ext_board_daily_snap
-- ----------------------------
ALTER TABLE "public"."ext_board_daily_snap" ADD CONSTRAINT "ext_board_daily_snap_board_id_fkey" FOREIGN KEY ("board_id") REFERENCES "public"."ext_board_list" ("id") ON DELETE CASCADE ON UPDATE NO ACTION;
ALTER TABLE "public"."ext_board_daily_snap" ADD CONSTRAINT "ext_board_daily_snap_stock_code_fkey" FOREIGN KEY ("stock_code") REFERENCES "public"."stocks" ("stock_code") ON DELETE CASCADE ON UPDATE NO ACTION;

-- ----------------------------
-- Foreign Keys structure for table ext_board_heat_daily
-- ----------------------------
ALTER TABLE "public"."ext_board_heat_daily" ADD CONSTRAINT "ext_board_heat_daily_board_id_fkey" FOREIGN KEY ("board_id") REFERENCES "public"."ext_board_list" ("id") ON DELETE CASCADE ON UPDATE NO ACTION;

-- ----------------------------
-- Foreign Keys structure for table ext_board_list
-- ----------------------------
ALTER TABLE "public"."ext_board_list" ADD CONSTRAINT "ext_board_list_provider_id_fkey" FOREIGN KEY ("provider_id") REFERENCES "public"."ext_providers" ("id") ON DELETE CASCADE ON UPDATE NO ACTION;

-- ----------------------------
-- Foreign Keys structure for table ext_board_local_map
-- ----------------------------
ALTER TABLE "public"."ext_board_local_map" ADD CONSTRAINT "ext_board_local_map_ext_board_id_fkey" FOREIGN KEY ("ext_board_id") REFERENCES "public"."ext_board_list" ("id") ON DELETE CASCADE ON UPDATE NO ACTION;
ALTER TABLE "public"."ext_board_local_map" ADD CONSTRAINT "ext_board_local_map_local_sector_id_fkey" FOREIGN KEY ("local_sector_id") REFERENCES "public"."sectors" ("id") ON DELETE CASCADE ON UPDATE NO ACTION;

-- ----------------------------
-- Foreign Keys structure for table user_roles
-- ----------------------------
ALTER TABLE "public"."user_roles" ADD CONSTRAINT "user_roles_role_id_fkey" FOREIGN KEY ("role_id") REFERENCES "public"."roles" ("id") ON DELETE CASCADE ON UPDATE NO ACTION;
ALTER TABLE "public"."user_roles" ADD CONSTRAINT "user_roles_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "public"."users" ("id") ON DELETE CASCADE ON UPDATE NO ACTION;

-- ----------------------------
-- Foreign Keys structure for table user_sessions
-- ----------------------------
ALTER TABLE "public"."user_sessions" ADD CONSTRAINT "user_sessions_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "public"."users" ("id") ON DELETE CASCADE ON UPDATE NO ACTION;
