import type { ReactNode } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { RULES } from '@/lib/types'

// Player-facing summary of the rules in backend/src/durak_engine (see "Rules implemented" in the README).

function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="grid gap-1.5">
      <h3 className="font-medium">{title}</h3>
      <ul className="grid list-disc gap-1 pl-5 text-sm text-muted-foreground">{children}</ul>
    </section>
  )
}

export function Rules() {
  return (
    <Card id="rules">
      <CardHeader>
        <CardTitle>How to play</CardTitle>
        <CardDescription>
          Get rid of all your cards. The last player still holding cards is the durak, the fool.
        </CardDescription>
      </CardHeader>
      <CardContent className="grid gap-5">
        <Section title="Setup">
          <li>2–6 players. Everyone is dealt 6 cards from a 36-card (6–A) or 52-card (2–A) deck.</li>
          <li>The next card is turned face up under the deck. Its suit is trumps for the whole game.</li>
          <li>Whoever holds the lowest trump attacks first.</li>
        </Section>

        <Section title="Attacking and defending">
          <li>The attacker leads any card at the next player, the defender.</li>
          <li>
            The defender beats each attack card with a higher card of the same suit, or with any trump. A
            trump can only be beaten by a higher trump.
          </li>
          <li>
            Attackers may keep adding cards whose rank is already on the table. The first bout holds at most
            5 attack cards, later bouts 6, and never more than the defender had in hand when the bout began.
          </li>
          <li>If the defender can't or won't beat a card, they take every card on the table.</li>
        </Section>

        <Section title="End of a bout">
          <li>
            All cards beaten and the attackers have passed: the table is discarded and the defender attacks
            next.
          </li>
          <li>Defender took: the player after the defender attacks next, so the defender loses their turn.</li>
          <li>
            Everyone draws back up to 6, main attacker first and defender last. The face-up trump is the last
            card drawn.
          </li>
        </Section>

        <Section title="Winning">
          <li>Once the deck is empty, players who run out of cards are out and safe.</li>
          <li>The last player left holding cards is the durak. If everyone runs out together, it's a draw.</li>
        </Section>

        <Section title="Optional rules (chosen when creating a room)">
          {RULES.map(({ key, label, description }) => (
            <li key={key}>
              <span className="font-medium text-foreground">{label}:</span> {description.toLowerCase()}.
            </li>
          ))}
        </Section>
      </CardContent>
    </Card>
  )
}
