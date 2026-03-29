import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: 'export', // 👈 זה מה שחסר

  eslint: {
    ignoreDuringBuilds: true,
  },
  reactStrictMode: true,
};

export default nextConfig;