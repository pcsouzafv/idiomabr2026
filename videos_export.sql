--
-- PostgreSQL database dump
--

\restrict DBWOybk9BnTqfIn3ZX1uP3Vz30t7sq7yzqQyHI88ysY9XtWOg1ohYssKfyihNwc

-- Dumped from database version 15.15
-- Dumped by pg_dump version 15.15

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Data for Name: videos; Type: TABLE DATA; Schema: public; Owner: idiomasbr
--

INSERT INTO public.videos (id, title, description, youtube_id, youtube_url, thumbnail_url, level, category, tags, duration, views_count, order_index, is_active, is_featured, created_at, updated_at, published_at) VALUES (1, ' Vocabulário e Fonética IPA', 'A Linguística é a ciência que investiga a linguagem humana, buscando determinar as características que regulam as estruturas das línguas naturais. Tradicionalmente, o estudo dos sons é abordado pelas disciplinas de Fonética e Fonologia, ambas focadas no componente sonoro, porém com abordagens distintas.

A Fonética estuda os sons da fala, fornecendo métodos para sua descrição, classificação e transcrição. É uma ciência descritiva cujo objeto de estudo são os fones (sons propriamente ditos), representados por símbolos fonéticos entre colchetes. A Fonética se divide em articulatória (produção dos sons), acústica (transmissão dos sons) e auditiva/perceptual (percepção dos sons). Para linguistas, a compreensão dos conceitos fonéticos, como os que estruturam o Alfabeto Fonético Internacional (IPA), é crucial, especialmente no que tange aos lugares e modos de articulação e ao estado da glote.

A Fonologia, por sua vez, investiga o componente sonoro das línguas sob uma perspectiva organizacional, estudando como os sons se comportam e geram significado dentro de um sistema linguístico. A Fonologia se concentra nos fonemas, unidades sonoras abstratas que distinguem o significado, enquanto a Fonética captura a pronúncia real, incluindo alofones. Estudos em Fonética e Fonologia do Português Brasileiro (PB) investigam questões complexas, como o estatuto fonológico dos encontros vocálicos, explicado por padrões duracionais distintos.

O Alfabeto Fonético Internacional (IPA), desenvolvido no século XIX, é o sistema mais utilizado para a transcrição fonética, fornecendo um símbolo único para cada som distinto e padronizando a representação da linguagem falada.

Na análise dos sons, linguistas utilizam transcrições fonéticas (narrow), detalhadas e representadas entre colchetes para capturar a pronúncia exata e variações sutis, e transcrições fonêmicas (broad), simplificadas e representadas entre barras para indicar apenas os fonemas.

A compreensão da pronúncia, embasada na Fonética, é essencial para a comunicação eficaz em uma língua estrangeira, e sua ausência prejudica o aprendizado.', '16mBOecILJ0', 'https://youtu.be/16mBOecILJ0', 'https://img.youtube.com/vi/16mBOecILJ0/maxresdefault.jpg', 'A1', 'OTHER', 'Fonética IPA', 0, 5, 0, true, true, '2025-12-14 19:27:24.708632+00', '2025-12-14 23:01:41.257844+00', NULL);


--
-- Name: videos_id_seq; Type: SEQUENCE SET; Schema: public; Owner: idiomasbr
--

SELECT pg_catalog.setval('public.videos_id_seq', 1, true);


--
-- PostgreSQL database dump complete
--

\unrestrict DBWOybk9BnTqfIn3ZX1uP3Vz30t7sq7yzqQyHI88ysY9XtWOg1ohYssKfyihNwc

