## Create LibreChar credentials env sealed secret

```shell
kubectl create secret generic librechat-credentials-env -n ai --from-env-file=apps/base/ai/librechat-credentials.env --dry-run=client -o yaml | kubeseal -o yaml > apps/base/ai/librechat-credentials-env-sealed-secret.yaml
```

## Create Open-WebUI credentials env sealed secret

```shell
kubectl create secret generic openwebui-credentials-env -n ai --from-env-file=apps/base/ai/openwebui-credentials.env --dry-run=client -o yaml | kubeseal -o yaml > apps/base/ai/openwebui-credentials-env-sealed-secret.yaml
```

## Create searxng config 

```shell
kubectl create secret generic searxng-config -n ai --from-file=settings.yml=apps/base/ai/searxng-config.yaml --dry-run=client -o yaml | kubeseal -o yaml > apps/base/ai/searxng-config-sealed-secret.yaml
```
