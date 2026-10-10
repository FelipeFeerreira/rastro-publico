import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  reactStrictMode: true,
  output: "standalone",
  eslint: {
    ignoreDuringBuilds: false,
  },
  async rewrites() {
    const api = process.env.NEXT_PUBLIC_API_BASE_URL;
    if (!api) return [];
    return [];
  },
};

export default nextConfig;
