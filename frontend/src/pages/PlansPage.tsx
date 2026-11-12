import { Link } from "react-router";

import type { Plan } from "../api/types";
import { useAuth } from "../auth/AuthProvider";
import { StateMessage } from "../components/StateMessage";
import { useMyPayments, useMySubscription, usePlans } from "../hooks/useAccount";

const dateFormat = new Intl.DateTimeFormat("uk-UA", { day: "numeric", month: "long", year: "numeric" });

const STATUS_LABEL = { succeeded: "Оплачено", pending: "Очікує банк", failed: "Відхилено" } as const;

function features(plan: Plan): string[] {
  return [
    `Якість до ${plan.max_quality}`,
    plan.has_ads ? "Реклама перед фільмом" : "Без реклами",
    "Увесь каталог фільмів і серіалів",
    "Історія переглядів і «Вибране»",
  ];
}

export function PlansPage() {
  const { user } = useAuth();
  const plans = usePlans();
  const mine = useMySubscription();
  const payments = useMyPayments();
  const currentCode = mine.data?.plan.code;

  if (plans.isError) return <StateMessage title="Не вдалося завантажити тарифи" />;

  return (
    <section>
      <h1 className="page-title">Тарифи</h1>
      {mine.data?.subscription ? (
        <p className="muted">
          Ваш тариф <strong>{mine.data.plan.name}</strong> діє до{" "}
          {dateFormat.format(new Date(mine.data.subscription.expires_at))}
          <br />
          Повторна оплата продовжить його ще на {mine.data.plan.period_days} днів.
        </p>
      ) : (
        <p className="muted">Дивіться без реклами та в Full HD з тарифом Premium.</p>
      )}

      <div className="plans">
        {plans.data?.map((plan) => {
          const current = plan.code === currentCode;
          const free = Number(plan.price) === 0;
          return (
            <article key={plan.id} className={`plan ${current ? "plan--current" : ""} ${free ? "" : "plan--paid"}`}>
              {current && <span className="plan__badge">Ваш тариф</span>}
              <h2 className="plan__name">{plan.name}</h2>
              <p className="plan__price">
                {free ? "0 грн" : `${Number(plan.price).toFixed(0)} грн`}
                <span className="muted"> / {plan.period_days} днів</span>
              </p>
              <ul className="plan__features">
                {features(plan).map((feature) => (
                  <li key={feature}>{feature}</li>
                ))}
              </ul>
              {free ? (
                <span className="muted plan__note">Діє для всіх без оплати</span>
              ) : !user ? (
                <Link to="/login?next=%2Fplans" className="button">
                  Увійти, щоб оформити
                </Link>
              ) : (
                <Link to={`/checkout?plan=${plan.code}`} className="button">
                  {current ? "Продовжити" : `Оформити ${plan.name}`}
                </Link>
              )}
            </article>
          );
        })}
      </div>

      {user && payments.data && payments.data.length > 0 && (
        <>
          <h2 className="section-title">Історія платежів</h2>
          <table className="table">
            <thead>
              <tr>
                <th>Дата</th>
                <th>Тариф</th>
                <th>Сума</th>
                <th>Статус</th>
              </tr>
            </thead>
            <tbody>
              {payments.data.map((payment) => (
                <tr key={payment.id}>
                  <td>{dateFormat.format(new Date(payment.created_at))}</td>
                  <td>{payment.plan.name}</td>
                  <td>{Number(payment.amount).toFixed(2)} грн</td>
                  <td>
                    <span className={`status status--${payment.status}`}>{STATUS_LABEL[payment.status]}</span>
                    {payment.status === "pending" && (
                      <Link to={`/checkout?payment=${payment.id}`} className="link table__action">
                        Відкрити
                      </Link>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </>
      )}
    </section>
  );
}
