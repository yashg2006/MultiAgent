import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { getMe, register, signIn, signOut } from "../api";

export function useMe() {
  return useQuery({ queryKey: ["me"], queryFn: getMe, staleTime: 60_000, retry: false });
}

type Credentials = { email: string; password: string };

/** Sign in or register; on success the user is cached and every other query refetched. */
export function useAuthAction(mode: "signin" | "register") {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ email, password }: Credentials) =>
      mode === "signin" ? signIn(email, password) : register(email, password),
    onSuccess: (user) => {
      queryClient.removeQueries({ predicate: (q) => q.queryKey[0] !== "me" });
      queryClient.setQueryData(["me"], user);
    },
  });
}

export function useSignOut() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: signOut,
    onSuccess: () => {
      // Drop everything cached for the previous user.
      queryClient.clear();
      queryClient.setQueryData(["me"], null);
    },
  });
}
