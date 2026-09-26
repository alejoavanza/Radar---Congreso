-- Apply only to the administrator-selected Supabase project after review.
-- This file does not create a project, enable billing or grant browser access.
-- YouTube public statistics expire at 29 days. Do not retain expired backups.
begin;
create table if not exists public.radar_follower_observations_v1 (
  member_id text not null,
  platform text not null check (platform = 'youtube'),
  account_id text not null check (account_id ~ '^UC[A-Za-z0-9_-]{22}$'),
  account_url text not null,
  followers bigint not null check (followers between 0 and 9999999999999),
  observed_at timestamptz not null,
  observed_day date generated always as ((observed_at at time zone 'UTC')::date) stored,
  expires_at timestamptz not null,
  source_kind text not null check (source_kind = 'official_api'),
  source_name text not null check (source_name = 'YouTube Data API'),
  precision text not null check (precision = 'rounded_down_3_significant_figures'),
  primary key (member_id, platform, account_id, observed_day),
  check (expires_at > observed_at and expires_at <= observed_at + interval '29 days'),
  check (account_url = 'https://www.youtube.com/channel/' || account_id)
);
alter table public.radar_follower_observations_v1 enable row level security;
revoke all on public.radar_follower_observations_v1 from public, anon, authenticated;

create or replace function public.radar_follower_history(p_member_id text, p_platform text, p_account_id text)
returns setof public.radar_follower_observations_v1
language plpgsql security definer set search_path = '' as $$
begin
  delete from public.radar_follower_observations_v1 where expires_at <= now();
  return query select * from public.radar_follower_observations_v1
    where member_id = p_member_id and platform = p_platform and account_id = p_account_id
      and expires_at > now() and observed_at > now() - interval '29 days'
      and observed_at <= now()
    order by observed_at asc limit 30;
end;
$$;

create or replace function public.radar_record_followers(p_observation jsonb)
returns setof public.radar_follower_observations_v1
language plpgsql security definer set search_path = '' as $$
declare
  stamp timestamptz := (p_observation->>'observed_at')::timestamptz;
begin
  if stamp is null or stamp > now() + interval '1 minute' or stamp < now() - interval '1 day' then
    raise exception 'Invalid observation timestamp';
  end if;
  delete from public.radar_follower_observations_v1 where expires_at <= now();
  insert into public.radar_follower_observations_v1
    (member_id, platform, account_id, account_url, followers, observed_at, expires_at,
     source_kind, source_name, precision)
  values (p_observation->>'member_id', p_observation->>'platform', p_observation->>'account_id',
    p_observation->>'account_url', (p_observation->>'followers')::bigint, stamp,
    stamp + interval '29 days', p_observation->>'source_kind',
    p_observation->>'source_name', p_observation->>'precision')
  on conflict (member_id, platform, account_id, observed_day) do nothing;
  -- Preserve the first observation of the UTC date; never refresh its age.
  return query select * from public.radar_follower_observations_v1
    where member_id = p_observation->>'member_id'
      and platform = p_observation->>'platform' and account_id = p_observation->>'account_id'
      and observed_day = (stamp at time zone 'UTC')::date and expires_at > now();
end;
$$;
revoke all on function public.radar_follower_history(text, text, text) from public, anon, authenticated;
revoke all on function public.radar_record_followers(jsonb) from public, anon, authenticated;
grant execute on function public.radar_follower_history(text, text, text) to service_role;
grant execute on function public.radar_record_followers(jsonb) to service_role;
commit;

-- Required before enabling production storage: enable pg_cron in Supabase, then
-- run this block. The 29-day expiry plus hourly cleanup stays below 30 days.
-- Verify job execution and backup retention before setting SOCIAL_SUPABASE_*.
-- select cron.schedule('radar-follower-expiry-v1', '0 * * * *',
--   'delete from public.radar_follower_observations_v1 where expires_at <= now()');
