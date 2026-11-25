# 可选 GitHub Pages 站点

从仓库根目录执行 `python -m pip install -r requirements.txt -r requirements-site.txt` 和 `python -m scripts.build_site`。构建结果在 `out/site/`。用 `python -m http.server 8000 --directory out/site` 预览。

MkDocs 从同一套 Markdown、资源注册表与词表生成导航和全文检索。网站收录审核状态为 `published` 的指南。GitHub 仓库保留编辑草稿与专业审核材料供贡献者检查。

Pages 尚未启用。合并后，在 GitHub 的 **Settings → Pages → Build and deployment → Source** 选择 **GitHub Actions**。在 repository variables 添加 `ENABLE_PAGES=true`，使用默认分支触发 Pages site 并核对 deployment URL。[GitHub 自定义 Pages 工作流](https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages)。
