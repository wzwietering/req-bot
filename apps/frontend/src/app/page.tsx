import { Navigation, Footer } from '../components/layout';
import { Hero, Features, HowItWorks, SocialProof, FinalCTA } from '../components/sections';

export default function Home() {
  return (
    <div className="min-h-screen">
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:absolute focus:top-4 focus:left-4 focus:z-50 focus:px-4 focus:py-2 focus:bg-jasper-red-500 focus:text-white focus:rounded focus:outline-2 focus:outline-benzol-green-500"
      >
        Skip to main content
      </a>
      <Navigation />
      <main id="main-content">
        <Hero />
        <Features />
        <HowItWorks />
        <SocialProof />
        <FinalCTA />
      </main>
      <Footer />
    </div>
  );
}
