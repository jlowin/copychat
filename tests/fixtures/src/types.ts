interface User {
  id: number;
  name: string;
  email: string;
}

type UserRole = "admin" | "user" | "guest";

export { User, UserRole };
