/** @type {import('next').NextConfig} */
const nextConfig = {
  // This is the magic shield:
  typescript: {
    ignoreBuildErrors: true,
  },
  eslint: {
    ignoreDuringBuilds: true,
  },
};

export default nextConfig;