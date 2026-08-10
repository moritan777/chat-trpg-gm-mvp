export function appendTextMessage(container: HTMLElement, speaker: string, content: string): void {
  const item = document.createElement("div");
  item.className = "message";
  const label = document.createElement("strong");
  label.textContent = `${speaker}: `;
  const text = document.createElement("span");
  text.textContent = content;
  item.append(label, text);
  container.append(item);
}
