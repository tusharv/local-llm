import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig(({ mode }) => {
  const siteUrl = loadEnv(mode, process.cwd(), "VITE_").VITE_PUBLIC_SITE_URL?.trim();
  const publicOrigin = siteUrl ? new URL(siteUrl) : null;
  if (publicOrigin && !["http:", "https:"].includes(publicOrigin.protocol)) {
    throw new Error("VITE_PUBLIC_SITE_URL must use http or https.");
  }
  return {
    plugins: [react(), {
      name: "studio-sharing-metadata",
      transformIndexHtml(html) {
        if (!publicOrigin) return html;
        const origin = publicOrigin.origin;
        return {
          html: html.replaceAll('content="/brand/og-image-v2.png"', `content="${origin}/brand/og-image-v2.png"`),
          tags: [
            { tag: "meta", attrs: { property: "og:url", content: `${origin}/` }, injectTo: "head" },
            { tag: "link", attrs: { rel: "canonical", href: `${origin}/` }, injectTo: "head" },
          ],
        };
      },
    }],
    server: { proxy: { "/api": "http://127.0.0.1:8000", "/uploads": "http://127.0.0.1:8000" } },
  };
});
