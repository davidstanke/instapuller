select * from posts;
select count(distinct username) from posts;
select distinct username from posts;
select count(*) from posts;

select username, count(username) from posts 
	group by username 
    order by count(username) desc;

select username from posts 
	group by username
    order by username;

    
select * from posts
	order by updated_at desc;