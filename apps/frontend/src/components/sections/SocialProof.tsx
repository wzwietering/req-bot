import { Container } from '../ui';

export function SocialProof() {
  const trustIndicators = [
    {
      icon: (
        <svg className="w-8 h-8" fill="currentColor" viewBox="0 0 24 24">
          <path d="M12 2L3 7l9 5 9-5-9-5zM3 17l9 5 9-5M3 12l9 5 9-5" />
        </svg>
      ),
      title: "Enterprise Ready",
      description: "OAuth authentication and secure data handling"
    },
    {
      icon: (
        <svg className="w-8 h-8" fill="currentColor" viewBox="0 0 20 20">
          <path fillRule="evenodd" d="M2.166 4.999A11.954 11.954 0 0010 1.944 11.954 11.954 0 0017.834 5c.11.65.166 1.32.166 2.001 0 5.225-3.34 9.67-8 11.317C5.34 16.67 2 12.225 2 7c0-.682.057-1.35.166-2.001zm11.541 3.708a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
        </svg>
      ),
      title: "Privacy First",
      description: "Your data stays secure and private"
    },
    {
      icon: (
        <svg className="w-8 h-8" fill="currentColor" viewBox="0 0 24 24">
          <path d="M13 10V3L4 14h7v7l9-11h-7z" />
        </svg>
      ),
      title: "Fast & Reliable",
      description: "Get comprehensive requirements in minutes"
    }
  ];

  return (
    <section className="py-20 bg-white">
      <Container>
        {/* Trust Indicators Header */}
        <div className="text-center mb-16">
          <h2 className="text-section-heading text-deep-indigo-500 mb-4">
            Built for Professional Development Teams
          </h2>
          <p className="text-lead text-deep-indigo-300 max-w-2xl mx-auto">
            Secure, reliable, and designed with enterprise-grade requirements gathering in mind
          </p>
        </div>

        {/* Trust Indicators */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
          {trustIndicators.map((indicator, index) => (
            <div key={index} className="text-center">
              <div className="inline-flex items-center justify-center w-16 h-16 bg-benzol-green-100 text-benzol-green-600 rounded-full mb-4">
                {indicator.icon}
              </div>
              <h3 className="text-feature-title text-deep-indigo-500 mb-2">
                {indicator.title}
              </h3>
              <p className="text-body text-deep-indigo-300">
                {indicator.description}
              </p>
            </div>
          ))}
        </div>

        {/* Technology Trust */}
        <div className="mt-16 bg-gradient-to-r from-deep-indigo-500 to-deep-indigo-600 rounded-2xl p-8 text-white text-center">
          <h3 className="text-feature-title mb-6">Powered by Leading AI Providers</h3>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            <div>
              <div className="text-2xl font-bold mb-2">Anthropic Claude</div>
              <div className="text-deep-indigo-100">Advanced reasoning and comprehensive questioning</div>
            </div>
            <div>
              <div className="text-2xl font-bold mb-2">OpenAI GPT</div>
              <div className="text-deep-indigo-100">Intelligent follow-up and context understanding</div>
            </div>
            <div>
              <div className="text-2xl font-bold mb-2">Google Gemini</div>
              <div className="text-deep-indigo-100">Multi-modal analysis and documentation</div>
            </div>
          </div>
        </div>
      </Container>
    </section>
  );
}