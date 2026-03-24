use std::{env, fs, process};

use bastion_forward_acl::{
    config::{ForwardingPolicy, RemoteForwardRequest},
    forwarding::remote_acl::evaluate_request,
};
use serde::de::DeserializeOwned;

fn load_json<T>(path: &str) -> T
where
    T: DeserializeOwned,
{
    let raw = fs::read_to_string(path).unwrap_or_else(|err| {
        eprintln!("failed to read {path}: {err}");
        process::exit(1);
    });

    serde_json::from_str(&raw).unwrap_or_else(|err| {
        eprintln!("failed to parse {path}: {err}");
        process::exit(1);
    })
}

fn main() {
    let args: Vec<String> = env::args().collect();
    if args.len() != 3 {
        eprintln!("usage: acl_probe <policy.json> <request.json>");
        process::exit(1);
    }

    let policy: ForwardingPolicy = load_json(&args[1]);
    let request: RemoteForwardRequest = load_json(&args[2]);
    let decision = evaluate_request(&policy, &request);

    println!(
        "{}",
        serde_json::to_string(&decision).expect("decision should serialize")
    );
}
