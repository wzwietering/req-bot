import { Container } from '../ui';
import { CTAHeader } from './CTAHeader';
import { CTAButtons } from './CTAButtons';
import { TrustIndicators } from './TrustIndicators';
import { ValueProposition } from './ValueProposition';

export function FinalCTA() {
  return (
    <section className="py-20 bg-gradient-to-br from-deep-indigo-50 to-benzol-green-50">
      <Container>
        <CTAHeader />
        <CTAButtons />
        <TrustIndicators />
        <ValueProposition />
      </Container>
    </section>
  );
}