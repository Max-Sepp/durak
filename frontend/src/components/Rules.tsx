import type { ReactNode } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import type { RoomSettings } from '@/lib/types'

// Player-facing summary of the rules in backend/src/durak_engine (see "Rules implemented" in the README),
// written for one room's settings.

function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="grid gap-1.5">
      <h3 className="font-medium">{title}</h3>
      <ul className="grid list-disc gap-1 pl-5 text-sm text-muted-foreground">{children}</ul>
    </section>
  )
}

export function Rules({ settings }: { settings: RoomSettings }) {
  const lowest = settings.deck_size === 36 ? '6' : '2'
  const others = settings.all_players_throw_in ? 'Every other player' : 'The attacker'

  return (
    <Card id="rules">
      <CardHeader>
        <CardTitle>How to play</CardTitle>
        <CardDescription>
          {settings.first_out_wins
            ? 'Be the first to get rid of all your cards.'
            : 'Get rid of all your cards. The last player still holding cards is the durak, the fool.'}{' '}
          These rules follow the settings above.
        </CardDescription>
      </CardHeader>
      <CardContent className="grid gap-5">
        <Section title="Setup">
          <li>
            2–6 players. Everyone is dealt 6 cards from a {settings.deck_size}-card deck ({lowest}–A).
          </li>
          <li>The next card is turned face up under the deck. Its suit is trumps for the whole game.</li>
          <li>Whoever holds the lowest trump attacks first.</li>
          {settings.trump_swap_enabled && (
            <li>
              Whoever holds the {lowest} of trumps may swap it for the face-up trump card at any time, until
              that card is drawn.
            </li>
          )}
        </Section>

        <Section title="Attacking and defending">
          <li>The attacker leads any card at the next player, the defender.</li>
          <li>
            The defender beats each attack card with a higher card of the same suit, or with any trump. A
            trump can only be beaten by a higher trump.
          </li>
          {settings.transfer_enabled && (
            <li>
              Before beating anything, the defender may instead add a card of the same rank to pass the whole
              attack on to the next player, if that player holds enough cards.
            </li>
          )}
          <li>
            {others} may add cards whose rank is already on the table. The first bout holds at most 5 attack
            cards, later bouts 6, and never more than the defender had in hand when the bout began.
          </li>
          <li>
            If the defender can't or won't beat a card, they take every card on the table
            {settings.throw_in_after_take
              ? ', after the attackers have had a chance to add more.'
              : ' straight away.'}
          </li>
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
          {settings.first_out_wins ? (
            <>
              <li>Once the deck is empty, the first player to get all their cards down wins and the game ends.</li>
              <li>
                If several players run out in the same bout and the deck can't refill them, whoever got their
                last card down first wins.
              </li>
            </>
          ) : (
            <>
              <li>Once the deck is empty, players who run out of cards are out and safe.</li>
              <li>
                The last player left holding cards is the durak. If everyone runs out together, it's a draw.
              </li>
            </>
          )}
        </Section>
      </CardContent>
    </Card>
  )
}
