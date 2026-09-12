import { createClient } from '@supabase/supabase-js';

const supabaseUrl = import.meta.env.VITE_SUPABASE_URL || 'https://hysfjbecwcljddszcjui.supabase.co';
const supabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY || 'sb_publishable_UwSom1GLyDkoTDha4ykc-w__AO0LPaI';

export const supabase = createClient(supabaseUrl, supabaseAnonKey);
