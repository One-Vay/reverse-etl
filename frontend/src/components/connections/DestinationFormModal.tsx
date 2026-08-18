import { zodResolver } from "@hookform/resolvers/zod";
import { useEffect } from "react";
import { useForm } from "react-hook-form";

import type { Destination } from "@/api/types";
import { Button } from "@/components/ui/Button";
import { FormField } from "@/components/ui/FormField";
import { Input } from "@/components/ui/Input";
import { Modal } from "@/components/ui/Modal";
import { Select } from "@/components/ui/Select";
import { useCreateDestination, useUpdateDestination } from "@/hooks/useDestinations";
import { type DestinationFormValues, destinationSchema } from "@/lib/schemas";

interface DestinationFormModalProps {
  open: boolean;
  onClose: () => void;
  destination?: Destination | null;
}

const DEFAULT_VALUES: DestinationFormValues = {
  name: "",
  type: "bitrix24",
  api_url: "",
  auth_token: "",
};

// Each destination type authenticates differently, so its API URL and auth
// token mean different things — see the matching connector's module
// docstring (app/connectors/destinations/{bitrix24,amocrm}.py) for the
// authoritative contract this mirrors.
const TYPE_HINTS = {
  bitrix24: {
    urlPlaceholder: "https://your-domain.bitrix24.ru",
    urlHint: "Portal base URL, without /rest or the webhook path.",
    tokenPlaceholder: "1/xxxxxxxxxxxxxxxx",
    tokenHint: "Incoming webhook path: {user_id}/{webhook_code}.",
  },
  amocrm: {
    urlPlaceholder: "https://your-domain.amocrm.ru",
    urlHint: "Account base URL.",
    tokenPlaceholder: undefined,
    tokenHint: "Long-lived API token, sent as a Bearer token.",
  },
} as const;

export function DestinationFormModal({
  open,
  onClose,
  destination,
}: DestinationFormModalProps) {
  const isEditing = Boolean(destination);
  const createDestination = useCreateDestination();
  const updateDestination = useUpdateDestination();

  const {
    register,
    handleSubmit,
    reset,
    setError,
    watch,
    formState: { errors },
  } = useForm<DestinationFormValues>({
    resolver: zodResolver(destinationSchema),
    defaultValues: DEFAULT_VALUES,
  });

  const hints = TYPE_HINTS[watch("type")];

  useEffect(() => {
    if (!open) return;
    reset(
      destination
        ? {
            name: destination.name,
            type: destination.type,
            api_url: destination.api_url,
            auth_token: "",
          }
        : DEFAULT_VALUES,
    );
  }, [open, destination, reset]);

  const isSaving = createDestination.isPending || updateDestination.isPending;

  const onSubmit = async (values: DestinationFormValues) => {
    const { auth_token, ...rest } = values;
    try {
      if (isEditing && destination) {
        await updateDestination.mutateAsync({
          id: destination.id,
          input: auth_token ? values : rest,
        });
      } else {
        if (!auth_token) {
          setError("auth_token", { message: "Auth token is required" });
          return;
        }
        await createDestination.mutateAsync({ ...values, auth_token });
      }
      onClose();
    } catch {
      // Already surfaced to the user via the mutation's onError toast.
    }
  };

  return (
    <Modal
      open={open}
      onClose={onClose}
      title={isEditing ? "Edit destination" : "Connect a CRM destination"}
      description="Bitrix24 and AmoCRM instances can receive synced records."
    >
      <form onSubmit={handleSubmit(onSubmit)} className="flex flex-col gap-4">
        <FormField
          label="Name"
          htmlFor="destination-name"
          error={errors.name?.message}
          required
        >
          <Input
            id="destination-name"
            placeholder="Sales Bitrix24"
            {...register("name")}
          />
        </FormField>

        <FormField label="Type" htmlFor="destination-type" required>
          <Select id="destination-type" {...register("type")}>
            <option value="bitrix24">Bitrix24</option>
            <option value="amocrm">AmoCRM</option>
          </Select>
        </FormField>

        <FormField
          label="API URL"
          htmlFor="destination-api-url"
          error={errors.api_url?.message}
          hint={hints.urlHint}
          required
        >
          <Input
            id="destination-api-url"
            placeholder={hints.urlPlaceholder}
            {...register("api_url")}
          />
        </FormField>

        <FormField
          label="Auth token"
          htmlFor="destination-auth-token"
          error={errors.auth_token?.message}
          hint={isEditing ? "Leave blank to keep the current token" : hints.tokenHint}
          required={!isEditing}
        >
          <Input
            id="destination-auth-token"
            type="password"
            placeholder={isEditing ? "••••••••" : hints.tokenPlaceholder}
            {...register("auth_token")}
          />
        </FormField>

        <div className="mt-2 flex justify-end gap-2">
          <Button type="button" variant="outline" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" loading={isSaving}>
            {isEditing ? "Save changes" : "Connect destination"}
          </Button>
        </div>
      </form>
    </Modal>
  );
}
