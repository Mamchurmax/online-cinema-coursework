import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Link, Navigate, useLocation, useSearchParams } from "react-router";

import { billingApi } from "../api/billing";
import { ApiError } from "../api/client";
import type { Payment, PaymentScenario } from "../api/types";
import { useAuth } from "../auth/AuthProvider";
import { StateMessage } from "../components/StateMessage";
import { AFTER_PAYMENT_KEYS, useMyPayments, useMySubscription, usePlans } from "../hooks/useAccount";

const SCENARIOS: { value: PaymentScenario; title: string; description: string }[] = [
  { value: "success", title: "Успішна оплата", description: "Банк одразу підтверджує платіж." },
  {
    value: "pending",
    title: "Очікує підтвердження",
    description: "Банк відповість пізніше — відповідь можна змоделювати кнопкою.",
  },
  { value: "failed", title: "Відхилена оплата", description: "Банк відхиляє платіж." },
];

const dateFormat = new Intl.DateTimeFormat("uk-UA", { day: "numeric", month: "long", year: "numeric" });

export function CheckoutPage() {
  const { user, isLoading } = useAuth();
  const location = useLocation();
  const [params] = useSearchParams();
  const planCode = params.get("plan") ?? "premium";
  const resumeId = Number(params.get("payment")) || null;

  const queryClient = useQueryClient();
  const plans = usePlans();
  const myPayments = useMyPayments();
  const mine = useMySubscription();
  const [scenario, setScenario] = useState<PaymentScenario>("success");
  const [payment, setPayment] = useState<Payment | null>(null);

  const refreshAccount = () =>
    AFTER_PAYMENT_KEYS.forEach((queryKey) => queryClient.invalidateQueries({ queryKey }));

  const pay = useMutation({
    mutationFn: () => billingApi.pay(planCode, scenario),
    onSuccess: (result) => {
      setPayment(result);
      refreshAccount();
    },
  });
  const bank = useMutation({
    mutationFn: ({ id, approved }: { id: number; approved: boolean }) => billingApi.bankResponse(id, approved),
    onSuccess: (result) => {
      setPayment(result);
      refreshAccount();
    },
  });

  if (!isLoading && !user) {
    return <Navigate to={`/login?next=${encodeURIComponent(location.pathname + location.search)}`} replace />;
  }

  // Coming back to an unfinished payment from the payment history.
  const current = payment ?? (resumeId ? myPayments.data?.find((p) => p.id === resumeId) : undefined) ?? null;
  const plan = current?.plan ?? plans.data?.find((p) => p.code === planCode);

  if (plans.isSuccess && !plan) {
    return (
      <StateMessage title="Тариф не знайдено" action={<Link to="/plans" className="button">До тарифів</Link>} />
    );
  }
  if (!plan) return <div className="checkout skeleton" style={{ height: 320 }} aria-busy="true" />;

  return (
    <section className="checkout">
      <Link to="/plans" className="back-link">
        ← Тарифи
      </Link>
      <h1 className="page-title">Оформлення {plan.name}</h1>
      <div className="checkout__summary">
        <span>
          {plan.name} · {plan.period_days} днів · до {plan.max_quality}, без реклами
        </span>
        <strong>{Number(plan.price).toFixed(2)} грн</strong>
      </div>

      {current ? (
        <PaymentResult
          payment={current}
          expiresAt={mine.data?.subscription?.expires_at}
          busy={bank.isPending}
          onBankResponse={(approved) => bank.mutate({ id: current.id, approved })}
          onRetry={() => {
            setPayment(null);
            pay.reset();
          }}
        />
      ) : (
        <form
          className="checkout__form"
          onSubmit={(event) => {
            event.preventDefault();
            pay.mutate();
          }}
        >
          <p className="checkout__demo">
            Це демонстраційна оплата: дані картки не потрібні, гроші не списуються. Оберіть, як відповість банк.
          </p>
          <fieldset className="scenarios">
            <legend className="field__label">Сценарій оплати</legend>
            {SCENARIOS.map((option) => (
              <label key={option.value} className={`scenario ${scenario === option.value ? "scenario--active" : ""}`}>
                <input
                  type="radio"
                  name="scenario"
                  value={option.value}
                  checked={scenario === option.value}
                  onChange={() => setScenario(option.value)}
                />
                <span>
                  <strong>{option.title}</strong>
                  <span className="muted">{option.description}</span>
                </span>
              </label>
            ))}
          </fieldset>
          {pay.isError && (
            <p className="form-error" role="alert">
              {pay.error instanceof ApiError && pay.error.status === 400
                ? "Цей тариф не можна придбати."
                : "Не вдалося створити платіж. Спробуйте ще раз."}
            </p>
          )}
          <button className="button button--play" type="submit" disabled={pay.isPending}>
            {pay.isPending ? "Обробка…" : `Сплатити ${Number(plan.price).toFixed(2)} грн`}
          </button>
        </form>
      )}
    </section>
  );
}

function PaymentResult({
  payment,
  expiresAt,
  busy,
  onBankResponse,
  onRetry,
}: {
  payment: Payment;
  expiresAt?: string;
  busy: boolean;
  onBankResponse: (approved: boolean) => void;
  onRetry: () => void;
}) {
  if (payment.status === "succeeded") {
    return (
      <div className="payment-result payment-result--ok" role="status">
        <h2>Оплату отримано</h2>
        <p>
          {payment.plan.name} активовано
          {expiresAt ? ` до ${dateFormat.format(new Date(expiresAt))}` : ""}
        </p>
        <p>Приємного перегляду без реклами!</p>
        <Link to="/" className="button">
          До каталогу
        </Link>
      </div>
    );
  }

  if (payment.status === "failed") {
    return (
      <div className="payment-result payment-result--failed" role="alert">
        <h2>Оплата не пройшла</h2>
        <p>Банк відхилив платіж. Підписка не змінилася.</p>
        <button className="button" onClick={onRetry}>
          Спробувати ще раз
        </button>
      </div>
    );
  }

  return (
    <div className="payment-result payment-result--pending" role="status">
      <h2>Очікуємо відповідь банку</h2>
      <p>
        Платіж №{payment.id} створено, але банк ще не відповів. Змоделюйте відповідь або залиште як є — адміністратор
        зможе підтвердити платіж пізніше.
      </p>
      <div className="payment-result__actions">
        <button className="button" disabled={busy} onClick={() => onBankResponse(true)}>
          Банк підтвердив
        </button>
        <button className="button button--ghost" disabled={busy} onClick={() => onBankResponse(false)}>
          Банк відхилив
        </button>
      </div>
    </div>
  );
}
