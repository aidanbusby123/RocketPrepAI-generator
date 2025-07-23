## GitHub Copilot Chat

- Extension Version: 0.25.1 (prod)
- VS Code: vscode/1.98.2
- OS: Linux

## Network

User Settings:
```json
  "github.copilot.advanced.debug.useElectronFetcher": true,
  "github.copilot.advanced.debug.useNodeFetcher": false,
  "github.copilot.advanced.debug.useNodeFetchFetcher": true
```

Connecting to https://api.github.com:
- DNS ipv4 Lookup: 140.82.116.5 (576 ms)
- DNS ipv6 Lookup: Error (497 ms): getaddrinfo ENOTFOUND api.github.com
- Proxy URL: None (19 ms)
- Electron fetch (configured): HTTP 200 (2025 ms)
- Node.js https: HTTP 200 (2046 ms)
- Node.js fetch: HTTP 200 (1069 ms)
- Helix fetch: HTTP 200 (2270 ms)

Connecting to https://api.individual.githubcopilot.com/_ping:
- DNS ipv4 Lookup: 140.82.113.21 (227 ms)
- DNS ipv6 Lookup: Error (160 ms): getaddrinfo ENOTFOUND api.individual.githubcopilot.com
- Proxy URL: None (14 ms)
- Electron fetch (configured): HTTP 200 (1222 ms)
- Node.js https: 