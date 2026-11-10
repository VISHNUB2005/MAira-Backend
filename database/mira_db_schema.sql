-- MAira PostgreSQL schema for local development.
-- Based on the DB team's PostgreSQL 18.6 dump, with these agreed changes:
-- 1. Native pg_catalog.gen_random_uuid() replaces the uuid-ossp dependency.
-- 2. User and admin password_hash columns allow NULL before registration.
-- 3. Admin table includes a name column.
-- Structure only: run the approved local seed.sql after this file.

-- Dumped from database version 18.6
-- Dumped by pg_dump version 18.6

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET transaction_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

CREATE SCHEMA sch_con;

SET default_tablespace = '';
SET default_table_access_method = heap;

CREATE TABLE sch_con.tb_con_admin (
    admin_id bigint NOT NULL,
    name character varying(150),
    email character varying(255) NOT NULL,
    password_hash text,
    status character varying(20) DEFAULT 'ACTIVE'::character varying NOT NULL,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp with time zone
);

CREATE SEQUENCE sch_con.tb_con_admin_admin_id_seq
    START WITH 1 INCREMENT BY 1 NO MINVALUE NO MAXVALUE CACHE 1;
ALTER SEQUENCE sch_con.tb_con_admin_admin_id_seq OWNED BY sch_con.tb_con_admin.admin_id;

CREATE TABLE sch_con.tb_con_audit_log (
    audit_id bigint NOT NULL,
    actor_type character varying(20),
    actor_id bigint,
    action character varying(100) NOT NULL,
    entity_type character varying(80),
    entity_id character varying(100),
    event_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    details jsonb DEFAULT '{}'::jsonb,
    CONSTRAINT tb_con_audit_log_actor_type_check CHECK (
        ((actor_type)::text = ANY ((ARRAY['USER'::character varying, 'ADMIN'::character varying, 'SYSTEM'::character varying])::text[]))
    )
);

CREATE SEQUENCE sch_con.tb_con_audit_log_audit_id_seq
    START WITH 1 INCREMENT BY 1 NO MINVALUE NO MAXVALUE CACHE 1;
ALTER SEQUENCE sch_con.tb_con_audit_log_audit_id_seq OWNED BY sch_con.tb_con_audit_log.audit_id;

CREATE TABLE sch_con.tb_con_chat_sessions (
    chat_session_id uuid DEFAULT pg_catalog.gen_random_uuid() NOT NULL,
    account_type character varying(20) NOT NULL,
    account_id bigint NOT NULL,
    title character varying(255),
    is_deleted boolean DEFAULT false NOT NULL,
    deleted_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    CONSTRAINT tb_con_chat_sessions_account_type_check CHECK (
        ((account_type)::text = ANY ((ARRAY['USER'::character varying, 'ADMIN'::character varying])::text[]))
    )
);

CREATE TABLE sch_con.tb_con_messages (
    message_id uuid DEFAULT pg_catalog.gen_random_uuid() NOT NULL,
    chat_session_id uuid NOT NULL,
    sender character varying(20) NOT NULL,
    content text NOT NULL,
    reply_to_message_id uuid,
    status character varying(20) DEFAULT 'COMPLETED'::character varying NOT NULL,
    model_name character varying(120),
    input_tokens integer,
    output_tokens integer,
    response_time_ms integer,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp with time zone,
    CONSTRAINT tb_con_messages_sender_check CHECK (
        ((sender)::text = ANY ((ARRAY['USER'::character varying, 'ASSISTANT'::character varying])::text[]))
    ),
    CONSTRAINT tb_con_messages_status_check CHECK (
        ((status)::text = ANY ((ARRAY['PENDING'::character varying, 'COMPLETED'::character varying, 'FAILED'::character varying])::text[]))
    )
);

CREATE TABLE sch_con.tb_con_otp_verification (
    otp_id uuid DEFAULT pg_catalog.gen_random_uuid() NOT NULL,
    account_type character varying(20),
    account_id bigint,
    email character varying(255) NOT NULL,
    otp_hash character varying(255) NOT NULL,
    purpose character varying(30) NOT NULL,
    expires_at timestamp with time zone NOT NULL,
    attempts smallint DEFAULT 0 NOT NULL,
    max_attempts smallint DEFAULT 5 NOT NULL,
    verified_at timestamp with time zone,
    used_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    CONSTRAINT tb_con_otp_verification_account_type_check CHECK (
        ((account_type)::text = ANY ((ARRAY['USER'::character varying, 'ADMIN'::character varying])::text[]))
    )
);

CREATE TABLE sch_con.tb_con_user (
    user_id bigint NOT NULL,
    email character varying(255) NOT NULL,
    user_type character varying(20) NOT NULL,
    password_hash text,
    status character varying(20) DEFAULT 'ACTIVE'::character varying NOT NULL,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp with time zone,
    CONSTRAINT tb_con_user_status_check CHECK (
        ((status)::text = ANY ((ARRAY['ACTIVE'::character varying, 'INACTIVE'::character varying, 'LOCKED'::character varying])::text[]))
    ),
    CONSTRAINT tb_con_user_user_type_check CHECK (
        ((user_type)::text = ANY ((ARRAY['STUDENT'::character varying, 'FACULTY'::character varying])::text[]))
    )
);

CREATE TABLE sch_con.tb_con_user_sessions (
    session_id uuid DEFAULT pg_catalog.gen_random_uuid() NOT NULL,
    account_type character varying(20) NOT NULL,
    account_id bigint NOT NULL,
    refresh_token_hash text NOT NULL,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    expires_at timestamp with time zone NOT NULL,
    last_used_at timestamp with time zone,
    revoked_at timestamp with time zone,
    is_revoked boolean DEFAULT false NOT NULL,
    CONSTRAINT tb_con_user_sessions_account_type_check CHECK (
        ((account_type)::text = ANY ((ARRAY['USER'::character varying, 'ADMIN'::character varying])::text[]))
    )
);

CREATE SEQUENCE sch_con.tb_con_user_user_id_seq
    START WITH 1 INCREMENT BY 1 NO MINVALUE NO MAXVALUE CACHE 1;
ALTER SEQUENCE sch_con.tb_con_user_user_id_seq OWNED BY sch_con.tb_con_user.user_id;

ALTER TABLE ONLY sch_con.tb_con_admin
    ALTER COLUMN admin_id SET DEFAULT nextval('sch_con.tb_con_admin_admin_id_seq'::regclass);
ALTER TABLE ONLY sch_con.tb_con_audit_log
    ALTER COLUMN audit_id SET DEFAULT nextval('sch_con.tb_con_audit_log_audit_id_seq'::regclass);
ALTER TABLE ONLY sch_con.tb_con_user
    ALTER COLUMN user_id SET DEFAULT nextval('sch_con.tb_con_user_user_id_seq'::regclass);

ALTER TABLE ONLY sch_con.tb_con_admin
    ADD CONSTRAINT tb_con_admin_email_key UNIQUE (email);
ALTER TABLE ONLY sch_con.tb_con_admin
    ADD CONSTRAINT tb_con_admin_pkey PRIMARY KEY (admin_id);
ALTER TABLE ONLY sch_con.tb_con_audit_log
    ADD CONSTRAINT tb_con_audit_log_pkey PRIMARY KEY (audit_id);
ALTER TABLE ONLY sch_con.tb_con_chat_sessions
    ADD CONSTRAINT tb_con_chat_sessions_pkey PRIMARY KEY (chat_session_id);
ALTER TABLE ONLY sch_con.tb_con_messages
    ADD CONSTRAINT tb_con_messages_pkey PRIMARY KEY (message_id);
ALTER TABLE ONLY sch_con.tb_con_otp_verification
    ADD CONSTRAINT tb_con_otp_verification_pkey PRIMARY KEY (otp_id);
ALTER TABLE ONLY sch_con.tb_con_user
    ADD CONSTRAINT tb_con_user_email_key UNIQUE (email);
ALTER TABLE ONLY sch_con.tb_con_user
    ADD CONSTRAINT tb_con_user_pkey PRIMARY KEY (user_id);
ALTER TABLE ONLY sch_con.tb_con_user_sessions
    ADD CONSTRAINT tb_con_user_sessions_pkey PRIMARY KEY (session_id);
ALTER TABLE ONLY sch_con.tb_con_user_sessions
    ADD CONSTRAINT tb_con_user_sessions_refresh_token_hash_key UNIQUE (refresh_token_hash);

CREATE INDEX idx_audit_log_event_at ON sch_con.tb_con_audit_log USING btree (event_at DESC);
CREATE INDEX idx_messages_session_created ON sch_con.tb_con_messages USING btree (chat_session_id, created_at, message_id);
CREATE INDEX idx_otp_email_purpose ON sch_con.tb_con_otp_verification USING btree (email, purpose);
CREATE INDEX idx_user_sessions_account ON sch_con.tb_con_user_sessions USING btree (account_type, account_id);

ALTER TABLE ONLY sch_con.tb_con_messages
    ADD CONSTRAINT tb_con_messages_chat_session_id_fkey
    FOREIGN KEY (chat_session_id)
    REFERENCES sch_con.tb_con_chat_sessions(chat_session_id) ON DELETE CASCADE;

ALTER TABLE ONLY sch_con.tb_con_messages
    ADD CONSTRAINT tb_con_messages_reply_to_message_id_fkey
    FOREIGN KEY (reply_to_message_id)
    REFERENCES sch_con.tb_con_messages(message_id) ON DELETE SET NULL;
