-- Disposable CI database only. These are synthetic records, not public metrics.
begin;
select * from public.radar_record_followers(jsonb_build_object(
  'member_id','fixture-only','platform','youtube','account_id','UCaaaaaaaaaaaaaaaaaaaaaa',
  'account_url','https://www.youtube.com/channel/UCaaaaaaaaaaaaaaaaaaaaaa',
  'followers',100,'observed_at',now()-interval '1 minute','source_kind','official_api',
  'source_name','YouTube Data API','precision','rounded_down_3_significant_figures'));
select * from public.radar_record_followers(jsonb_build_object(
  'member_id','fixture-only','platform','youtube','account_id','UCaaaaaaaaaaaaaaaaaaaaaa',
  'account_url','https://www.youtube.com/channel/UCaaaaaaaaaaaaaaaaaaaaaa',
  'followers',200,'observed_at',now(),'source_kind','official_api',
  'source_name','YouTube Data API','precision','rounded_down_3_significant_figures'));
do $$
begin
  if (select count(*) from public.radar_follower_observations_v1) <> 1 then
    raise exception 'Repeated queries created more than one daily observation';
  end if;
  if (select followers from public.radar_follower_observations_v1) <> 100 then
    raise exception 'Repeated query overwrote the first dated observation';
  end if;
  if exists (select 1 from public.radar_follower_history('someone-else','youtube','UCaaaaaaaaaaaaaaaaaaaaaa')) then
    raise exception 'History leaked across identities';
  end if;
  if has_function_privilege('anon','public.radar_record_followers(jsonb)','execute')
     or has_function_privilege('authenticated','public.radar_follower_history(text,text,text)','execute')
     or has_table_privilege('anon','public.radar_follower_observations_v1','select') then
    raise exception 'Browser roles can access private snapshot data';
  end if;
  if not has_function_privilege('service_role','public.radar_record_followers(jsonb)','execute') then
    raise exception 'Backend role cannot call the restricted writer';
  end if;
end;
$$;
insert into public.radar_follower_observations_v1
 (member_id,platform,account_id,account_url,followers,observed_at,expires_at,source_kind,source_name,precision)
values ('fixture-expired','youtube','UCbbbbbbbbbbbbbbbbbbbbbb','https://www.youtube.com/channel/UCbbbbbbbbbbbbbbbbbbbbbb',
 1,now()-interval '29 days',now()-interval '1 minute','official_api','YouTube Data API','rounded_down_3_significant_figures');
select * from public.radar_follower_history('fixture-expired','youtube','UCbbbbbbbbbbbbbbbbbbbbbb');
do $$
begin
  if exists(select 1 from public.radar_follower_observations_v1 where member_id='fixture-expired') then
    raise exception 'Expired records were not physically deleted on read';
  end if;
end;
$$;
rollback;
