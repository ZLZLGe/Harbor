#!/bin/bash
set -euo pipefail

cat <<'EOF' > /app/workspace/src/forwarding/remote_acl.rs
use std::net::IpAddr;

use serde::Serialize;

use crate::config::{ForwardingPolicy, RemoteForwardRequest};

#[derive(Debug, Clone, PartialEq, Eq, Serialize)]
pub struct AclDecision {
    pub allowed: bool,
    pub reason: String,
}

impl AclDecision {
    fn allow() -> Self {
        Self {
            allowed: true,
            reason: "allowed".to_string(),
        }
    }

    fn deny(reason: &str) -> Self {
        Self {
            allowed: false,
            reason: reason.to_string(),
        }
    }
}

pub fn evaluate_request(policy: &ForwardingPolicy, request: &RemoteForwardRequest) -> AclDecision {
    if !policy
        .allowed_principals
        .iter()
        .any(|principal| principal == &request.principal)
    {
        return AclDecision::deny("principal-not-allowed");
    }

    let bind_host = normalize_host(&request.bind_host);
    let target_host = normalize_host(&request.target_host);

    if !host_in_allowlist(&bind_host, &policy.allowed_bind_hosts) || !is_loopback_host(&bind_host) {
        return AclDecision::deny("bind-host-not-allowed");
    }

    if !is_loopback_host(&target_host) {
        return AclDecision::deny("target-must-be-loopback");
    }

    if !policy
        .allowed_target_ports
        .iter()
        .any(|port| *port == request.target_port)
    {
        return AclDecision::deny("target-port-not-allowed");
    }

    AclDecision::allow()
}

fn host_in_allowlist(host: &str, allowlist: &[String]) -> bool {
    allowlist
        .iter()
        .any(|candidate| normalize_host(candidate) == host)
}

fn is_loopback_host(host: &str) -> bool {
    if host == "localhost" {
        return true;
    }

    host.parse::<IpAddr>()
        .map(|addr| addr.is_loopback())
        .unwrap_or(false)
}

fn normalize_host(raw: &str) -> String {
    raw.trim()
        .trim_matches(|ch| ch == '[' || ch == ']')
        .to_ascii_lowercase()
}
EOF
