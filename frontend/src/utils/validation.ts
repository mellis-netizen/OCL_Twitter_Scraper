import { z } from 'zod';

// Company validation schema
export const companySchema = z.object({
  name: z.string().min(1, 'Company name is required').max(100),
  aliases: z.array(z.string()).optional().default([]),
  tokens: z.array(z.string()).optional().default([]),
  priority: z.enum(['HIGH', 'MEDIUM', 'LOW']).optional().default('MEDIUM'),
  status: z.string().optional().default('active'),
  website: z.string().url('Invalid URL').optional().or(z.literal('')),
  twitter_handle: z.string().optional().or(z.literal('')),
  description: z.string().optional().or(z.literal('')),
  exclusions: z.array(z.string()).optional().default([]),
});

export type CompanyFormData = z.infer<typeof companySchema>;

// Feed validation schema
export const feedSchema = z.object({
  name: z.string().min(1, 'Feed name is required').max(200),
  url: z.string().url('Invalid URL').max(1000),
  type: z.string().optional().default('rss'),
  priority: z.number().min(1).max(5).optional().default(3),
  is_active: z.boolean().optional().default(true),
});

export type FeedFormData = z.infer<typeof feedSchema>;

// Login validation schema
export const loginSchema = z.object({
  username: z.string().min(3, 'Username must be at least 3 characters'),
  password: z.string().min(8, 'Password must be at least 8 characters'),
});

export type LoginFormData = z.infer<typeof loginSchema>;

// Register validation schema
export const registerSchema = z.object({
  username: z.string().min(3, 'Username must be at least 3 characters').max(50),
  email: z.string().email('Invalid email address'),
  password: z.string().min(8, 'Password must be at least 8 characters'),
  confirmPassword: z.string(),
}).refine((data) => data.password === data.confirmPassword, {
  message: "Passwords don't match",
  path: ['confirmPassword'],
});

export type RegisterFormData = z.infer<typeof registerSchema>;
