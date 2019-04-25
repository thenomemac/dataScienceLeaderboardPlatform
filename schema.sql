drop table if exists user;
create table user (
  user_id integer primary key autoincrement,
  username text not null,
  email text not null,
  pw_hash text not null
);

drop table if exists submission;
create table submission (
  submission_id integer primary key autoincrement,
  user_id integer not null,
  filename text not null,
  submit_date integer not null,
  public_score real not null,
  private_score real not null,
  total_score real not null
);

drop table if exists selection;
create table selection (
  user_id integer not null,
  select_nbr integer not null,
  submission_id integer not null,
  select_date integer not null
);
  
