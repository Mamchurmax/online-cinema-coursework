import { apiGet, apiRequest } from "./client";
import type { MySubscription, NotificationList, Payment, PaymentScenario, Plan, TitleListItem } from "./types";

export const billingApi = {
  plans: (signal?: AbortSignal) => apiGet<Plan[]>("/plans", undefined, signal),
  mySubscription: (signal?: AbortSignal) => apiGet<MySubscription>("/me/subscription", undefined, signal),
  myPayments: (signal?: AbortSignal) => apiGet<Payment[]>("/me/payments", undefined, signal),
  pay: (planCode: string, scenario: PaymentScenario) =>
    apiRequest<Payment>("POST", "/payments", { json: { plan_code: planCode, scenario } }),
  bankResponse: (paymentId: number, approved: boolean) =>
    apiRequest<Payment>("POST", `/payments/${paymentId}/bank-response`, { json: { approved } }),
};

export const notificationsApi = {
  list: (signal?: AbortSignal) => apiGet<NotificationList>("/me/notifications", { limit: 20 }, signal),
  markAllRead: () => apiRequest<{ unread_count: number }>("POST", "/me/notifications/read", { json: {} }),
};

export const favoritesApi = {
  list: (signal?: AbortSignal) => apiGet<TitleListItem[]>("/me/favorites", undefined, signal),
  ids: (signal?: AbortSignal) => apiGet<number[]>("/me/favorites/ids", undefined, signal),
  add: (titleId: number) => apiRequest<void>("PUT", `/me/favorites/${titleId}`),
  remove: (titleId: number) => apiRequest<void>("DELETE", `/me/favorites/${titleId}`),
};
