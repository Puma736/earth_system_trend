import { Suspense } from "react";
import { Skeleton, Stack } from "@mantine/core";
import { Workstation } from "@/components/workstation";

export default function AnalisisPage() {
  return (
    <Suspense
      fallback={
        <Stack p="md" gap="sm">
          <Skeleton height={72} radius="md" />
          <Skeleton height={420} radius="md" />
        </Stack>
      }
    >
      <Workstation />
    </Suspense>
  );
}
