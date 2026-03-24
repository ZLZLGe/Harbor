A Java CLI importer in `/root/plugin-manifest-importer` is used by a background job to ingest partner plugin manifests from disk.

The importer currently feeds manifest JSON directly into Jackson polymorphic step binding and then materializes each imported step into a normalized output file. The service only intends to support a small fixed set of plugin step kinds, but an uploaded manifest can currently smuggle dangerous type hints such as `@class` and instantiate internal step implementations that should never be reachable from partner input.

You need to:
1. Write patch files that fix this issue in `/root/patches/`
2. Apply the patches to the git repo at `/root/plugin-manifest-importer/`
3. Rebuild the importer with Maven:

```bash
cd /root/plugin-manifest-importer
mvn package -DskipTests
```

The verifier will run the rebuilt CLI against manifest files under `/root/manifests/`. Exploit manifests that rely on polymorphic type hints must be rejected, allowed plugin step kinds must still import successfully, and free-text fields that merely mention strings like `@class` must not be treated as an attack.
