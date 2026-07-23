from api.v1.auth import router
for r in router.routes:
    print(r.path)
