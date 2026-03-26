import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function getImageUrl(image: string | null): string {
  if (!image) {
    return "/public/placeholder.svg";
  }
  return image.startsWith("http")
    ? `${image}?t=${Date.now()}`
    : `/media/${image}`;
}
