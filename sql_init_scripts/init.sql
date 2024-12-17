create table session
(
    id    bigint       not null
        primary key,
    token varchar(255) null
);

create table auth
(
    id            bigint auto_increment
        primary key,
    token_type    varchar(255) null,
    access_token  varchar(255) null,
    expires_in    int          null,
    scope         varchar(255) null,
    refresh_token varchar(255) null,
    created_at    datetime     not null,
    expires_at    datetime     null,
    hash          varchar(64)  null,
    constraint auth_pk
        unique (id)
);

create table user
(
    user_id    bigint       not null
        primary key,
    auth_id    bigint       null,
    username   varchar(255) null,
    session_id bigint       null,
    constraint user_auth_id_fk
        foreign key (auth_id) references auth (id),
    constraint user_session_id_fk
        foreign key (session_id) references session (id)
);



create table meta
(
    user_id         bigint                                 not null
        primary key,
    last_message_id bigint                                 null,
    screen          enum ('MAIN', 'EMPTY') default 'EMPTY' not null,
    constraint meta_user_user_id_fk
        foreign key (user_id) references user (user_id)
);
