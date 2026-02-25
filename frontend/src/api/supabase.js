import { createClient } from '@supabase/supabase-js';

const supabaseUrl = import.meta.env.VITE_SUPABASE_URL || 'https://vqktgedbdqutrhiouhtq.supabase.co';
const supabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY || 'sb_publishable_h9S3w_oohOoehlWGQ9rm6g_VkbWCaq2';

export const supabase = createClient(supabaseUrl, supabaseAnonKey);
