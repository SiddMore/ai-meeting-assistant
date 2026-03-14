/** @type {import('next').NextConfig} */
const nextConfig = {
  typescript: {
    ignoreBuildErrors: true,
  },
  eslint: {
    ignoreDuringBuilds: true,
  },
  // We'll turn off standalone for a second to see if default works with Webpack
  // output: 'standalone', 
};

export default nextConfig;