A Java preview service in `/root/preview-service` exposes `POST /api/v1/preview`.

The endpoint currently binds the request JSON into a `PreviewRequest` and only then checks whether script preview mode is allowed. Because the transform block has a catch-all setter for unknown keys, an empty-string key can flip `scriptPolicy.enabled` back on during binding and bypass the intended restriction.

You need to:
1. Write patch files that fix this bypass in `/root/patches/`
2. Apply the patches to the git repo at `/root/preview-service/`
3. Rebuild the service with Maven:

```bash
cd /root/preview-service
mvn clean package -DskipTests
```

The verifier will restart the rebuilt service and send preview requests. Payloads that rely on the empty-key override must be rejected, normal field preview requests must still succeed, and harmless row data that merely contains the text `"": {"enabled": true}` inside a string value must not be treated as an exploit.
