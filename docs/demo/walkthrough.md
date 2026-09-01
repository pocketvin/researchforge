# Reproducible Walkthrough / 可复现实演

## Start / 启动

```bash
docker compose up -d --build --wait
uv run python scripts/docker_smoke.py
```

If Docker Hub is unreachable, the Compose build accepts `PYTHON_IMAGE`, `NODE_IMAGE`, `NGINX_IMAGE`, and `POSTGRES_IMAGE` overrides while retaining standard defaults.

若 Docker Hub 暂时不可达，可通过上述四个环境变量切换兼容镜像源；默认配置仍使用标准官方镜像名。

## What to verify / 核对内容

- Research: five task modes, asynchronous status, cancellation, ten-stage trace, API facts, deterministic checks, evidence links, counter-evidence, limitations, and sources.
- Skill Lab: persisted experiment status, failure cluster, Experience, Skill Diff, paired Validation evidence, sealed/consumed Final Test state, and negative outcomes without rewriting them as success.
- Research 页：五种任务、异步状态、取消、十阶段 Trace、API 事实、确定性核验、证据链、反证、限制和来源。
- Skill Lab：持久化实验状态、失败聚类、Experience、Skill Diff、Validation 配对证据、Final Test 封闭/消费状态及诚实负结果。

## Evidence / 证据

- `docs/assets/research-page.png`
- `docs/assets/skill-lab-page.png`
- `docs/assets/researchforge-v1.4-demo.mp4`
- `docs/evidence/g4-engineering-progress.md`

All screenshots use only public frozen fixtures. They do not contain an API key, hidden ground truth, or a real-user validation claim.

所有截图仅使用公开冻结样例，不含 API Key、隐藏标签或真实用户验证声明。
