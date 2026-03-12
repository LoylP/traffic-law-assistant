export type MessageRole = "user" | "assistant";

export type Message = {
  id: string;
  role: MessageRole;
  content: string;
  timestamp: string;
};

export type QuickAction = {
  id: string;
  label: string;
  prompt: string;
};
