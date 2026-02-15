export async function uploadImageToCloudinary(file: File): Promise<string> {
  const formData = new FormData();
  formData.append("image", file);

  const response = await fetch('http://localhost:8000/api/auth/upload-avatar/', {
    method: "POST",
    headers: {
      "Authorization": `Bearer ${localStorage.getItem("access_token")}`,
    },
    body: formData,
  });

  if (!response.ok) {
    throw new Error("Failed to upload image to Cloudinary");
  }

  const data = await response.json();
  return data.avatar_url as string;
}

interface User {
  id: number;
  firstName: string;
  lastName: string;
  email: string;
  username: string;
  avatar?: string;
  createdAt: string;
  dateJoined?: string;
  updatedAt?: string;
}

export async function updateUserAvatarUrl(avatarUrl: string): Promise<User> {
  const response = await fetch(`${process.env.REACT_APP_API_URL || 'http://localhost:8000/api'}/auth/avatar-url`, {
    method: "PATCH",
    headers: {
      "Content-Type": "application/json",
      "Authorization": `Bearer ${localStorage.getItem("access_token")}`,
    },
    body: JSON.stringify({
      avatar: avatarUrl,
    }),
  });

  if (!response.ok) {
    throw new Error("Failed to update avatar URL");
  }

  const data = await response.json();
  return data;
}
