export function reportLovableError(
  error: unknown,
  context: Record<string, unknown> = {}
) {
  console.error("[Error]", error, context);
}