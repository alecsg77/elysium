## Create LibreChar credentials env sealed secret

```shell
kubectl create secret generic librechat-credentials-env -n ai --from-env-file=apps/base/ai/librechat-credentials.env --dry-run=client -o yaml | kubeseal -o yaml > apps/base/ai/librechat-credentials-env-sealed-secret.yaml
```
