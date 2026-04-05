#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Playwright 企微扫码登录
打开 SCRM 前端 → 企微 SSO 二维码 → 用户扫码 → 自动捕获 sessionStorage.token
"""
import json
import os
import sys
import time
from datetime import datetime

from config import TOKEN_PATH, SCRM_FRONTEND_URL


def _check_playwright():
    """检查 Playwright 和 Chromium 是否可用"""
    try:
        from playwright.sync_api import sync_playwright
        return True
    except ImportError:
        print("❌ Playwright 未安装，请执行:")
        print("   pip3 install playwright")
        print("   python3 -m playwright install chromium")
        return False


def _save_token(token: str):
    """持久化 token 到磁盘"""
    TOKEN_PATH.parent.mkdir(parents=True, exist_ok=True)
    TOKEN_PATH.write_text(json.dumps({
        "token": token,
        "saved_at": datetime.now().isoformat(),
    }, ensure_ascii=False, indent=2), encoding="utf-8")


def qr_login(scrm_url: str = None, timeout: int = 120) -> str:
    """
    打开浏览器显示企微扫码页面，扫码后自动捕获 token。

    Args:
        scrm_url: SCRM 前端地址（默认 https://call-workweixin.zhenai.com）
        timeout:  等待扫码超时秒数

    Returns:
        捕获到的 token 字符串
    """
    if not _check_playwright():
        sys.exit(1)

    from playwright.sync_api import sync_playwright

    url = scrm_url or SCRM_FRONTEND_URL
    captured_tokens = []

    print("🔐 正在打开企微扫码登录页面...")
    print(f"   前端地址: {url}")
    print(f"   等待超时: {timeout} 秒")
    print("   👉 请用企业微信 APP 扫描二维码\n")

    with sync_playwright() as p:
        # 检测系统代理（Playwright 不自动继承环境变量代理）
        launch_opts = {
            "headless": False,
            "args": ["--window-size=960,720"],
        }
        proxy_url = (os.environ.get("HTTPS_PROXY")
                     or os.environ.get("HTTP_PROXY")
                     or os.environ.get("https_proxy")
                     or os.environ.get("http_proxy"))
        if proxy_url:
            launch_opts["proxy"] = {"server": proxy_url}
            print(f"   🌐 使用代理: {proxy_url}")

        browser = p.chromium.launch(**launch_opts)
        context = browser.new_context(
            viewport={"width": 960, "height": 720},
            ignore_https_errors=True,  # 内部 SSL 证书可能不被信任
        )
        page = context.new_page()

        # ── 策略 3: 拦截 API 响应中的 token ──
        def _on_response(response):
            try:
                if response.status == 200 and "workapi/user" in response.url:
                    body = response.json()
                    if isinstance(body, dict) and body.get("token"):
                        captured_tokens.append(body["token"])
            except Exception:
                pass

            try:
                if response.status == 200 and "qywxlogin" in response.url:
                    body = response.json()
                    if isinstance(body, dict) and body.get("token"):
                        captured_tokens.append(body["token"])
            except Exception:
                pass

        page.on("response", _on_response)

        try:
            page.goto(url, wait_until="domcontentloaded", timeout=30000)
            print("✅ 登录页面已打开，等待扫码...\n")

            start = time.time()
            token = None

            while time.time() - start < timeout:
                # ── 策略 0: 先检查响应拦截 ──
                if captured_tokens:
                    token = captured_tokens[0]
                    break

                # ── 策略 1: sessionStorage.token（文档明确） ──
                try:
                    val = page.evaluate("""() => {
                        const keys = ['token', 'accessToken', 'access_token',
                                      'userToken', 'scrm_token'];
                        for (const k of keys) {
                            let v = sessionStorage.getItem(k);
                            if (v) return v;
                            v = localStorage.getItem(k);
                            if (v) return v;
                        }
                        // userInfo 对象内的 token
                        for (const store of [sessionStorage, localStorage]) {
                            const ui = store.getItem('userInfo');
                            if (ui) {
                                try {
                                    const obj = JSON.parse(ui);
                                    if (obj && obj.token) return obj.token;
                                } catch(e) {}
                            }
                        }
                        return null;
                    }""")
                    if val:
                        token = val
                        break
                except Exception:
                    pass  # 页面可能正在跳转

                # ── 策略 2: URL 参数 ──
                current_url = page.url
                if "token=" in current_url:
                    from urllib.parse import urlparse, parse_qs
                    qs = parse_qs(urlparse(current_url).query)
                    if qs.get("token"):
                        token = qs["token"][0]
                        break

                # ── 策略 4: Cookie ──
                try:
                    for cookie in context.cookies():
                        if cookie["name"].lower() in ("token", "access_token"):
                            token = cookie["value"]
                            break
                    if token:
                        break
                except Exception:
                    pass

                # 进度提示
                elapsed = int(time.time() - start)
                if elapsed > 0 and elapsed % 15 == 0:
                    print(f"   ⏳ 等待扫码中... 已等 {elapsed}s / {timeout}s")

                time.sleep(1)

            if not token:
                print(f"\n❌ 扫码等待超时（{timeout}秒），请重试")
                sys.exit(1)

            # 清理 token
            token = token.strip().strip('"').strip("'")
            if token.lower().startswith("bearer "):
                token = token[7:]

            # 保存 + 验证
            _save_token(token)
            print(f"\n✅ Token 已捕获并保存")
            print(f"   Token: {token[:8]}...{token[-4:]}")
            print(f"   文件:  {TOKEN_PATH}")

            return token

        except KeyboardInterrupt:
            print("\n⚠️  用户取消")
            sys.exit(0)
        except Exception as e:
            print(f"\n❌ 登录过程出错: {e}")
            sys.exit(1)
        finally:
            browser.close()


if __name__ == "__main__":
    qr_login()
