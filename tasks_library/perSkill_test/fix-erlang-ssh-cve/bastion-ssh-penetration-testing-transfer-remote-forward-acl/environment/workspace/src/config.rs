use serde::Deserialize;

#[derive(Debug, Clone, Deserialize)]
pub struct ForwardingPolicy {
    pub allowed_principals: Vec<String>,
    pub allowed_bind_hosts: Vec<String>,
    pub allowed_target_ports: Vec<u16>,
}

#[derive(Debug, Clone, Deserialize)]
pub struct RemoteForwardRequest {
    pub principal: String,
    pub bind_host: String,
    pub bind_port: u16,
    pub target_host: String,
    pub target_port: u16,
}
