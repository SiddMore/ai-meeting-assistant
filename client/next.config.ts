/** @type {import('next').NextConfig} */
const nextConfig = {
  // Keep our "Shields"
  typescript: {
    ignoreBuildErrors: true,
  },
  eslint: {
    ignoreDuringBuilds: true,
  },
  
  // THE FIX: Bundles everything correctly for Vercel
  output: 'standalone', 
};

export default nextConfig;