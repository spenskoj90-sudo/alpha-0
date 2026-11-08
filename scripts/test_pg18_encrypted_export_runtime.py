"""Two local, synthetic PG18 clusters; never contacts Neon/B2 or real data."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

from pg18_encrypted_export import encrypted_export

TOOLS = ('initdb','pg_ctl','psql','pg_restore','pg_dump','pg_dumpall','age','age-keygen')
READY = all(shutil.which(t) for t in TOOLS) and os.getuid() != 0
if os.environ.get('G3_REQUIRE_RUNTIME') == '1' and not READY:
    raise RuntimeError('required synthetic PG18/age runtime unavailable')

@unittest.skipUnless(READY, 'local non-root PG18 and age required')
class RuntimeTests(unittest.TestCase):
    def test_encrypted_full_export_restores_data_owners_grants_and_force_rls(self):
        def run(args, **kw):
            return subprocess.run(args, check=True, stdout=subprocess.PIPE,
                                  stderr=subprocess.PIPE, timeout=60, **kw).stdout
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); root.chmod(0o700)
            clusters = []
            try:
                for name, user, port in [('source','source_admin',55431),('target','restore_admin',55432)]:
                    data=root/name; sock=root/(name+'socket'); sock.mkdir()
                    run(['initdb','-D',str(data),'-U',user,'--auth=trust','--no-locale'])
                    run(['pg_ctl','-D',str(data),'-l',str(root/(name+'.log')),
                         '-o',f"-k {sock} -h '' -p {port}",'-w','start'])
                    clusters.append(data)
                source=['-h',str(root/'sourcesocket'),'-p','55431','-U','source_admin']
                target=['-h',str(root/'targetsocket'),'-p','55432','-U','restore_admin']
                run(['psql',*source,'-d','postgres','-v','ON_ERROR_STOP=1'], input=b'''
CREATE ROLE fixture_owner NOLOGIN;
CREATE ROLE fixture_reader NOLOGIN;
CREATE DATABASE sentinel_fixture OWNER fixture_owner;
''')
                run(['psql',*source,'-d','sentinel_fixture','-v','ON_ERROR_STOP=1'], input=b'''
SET ROLE fixture_owner;
CREATE SCHEMA neon_auth AUTHORIZATION fixture_owner;
CREATE TABLE public.fixture(id integer PRIMARY KEY, secret text);
INSERT INTO public.fixture VALUES (1,'synthetic'),(2,'synthetic-only');
CREATE TABLE neon_auth.fixture(id integer PRIMARY KEY);
INSERT INTO neon_auth.fixture VALUES (7);
ALTER TABLE public.fixture ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.fixture FORCE ROW LEVEL SECURITY;
CREATE POLICY fixture_select ON public.fixture FOR SELECT TO fixture_reader USING (id=1);
GRANT USAGE ON SCHEMA public,neon_auth TO fixture_reader;
GRANT SELECT ON public.fixture,neon_auth.fixture TO fixture_reader;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO fixture_reader;
''')
                key=root/'identity'; run(['age-keygen','-o',str(key)])
                recipient=run(['age-keygen','-y',str(key)]).decode().strip()
                config=root/'service'; config.write_text(f'[source]\nhost={root}/sourcesocket\nport=55431\nuser=source_admin\ndbname=sentinel_fixture\n')
                config.chmod(0o600)
                output=root/'encrypted'; output.mkdir(mode=0o700)
                parts=encrypted_export(output=output,service_file=config,service='source',
                                       recipient=recipient,max_bytes=1024*1024)
                def restore(part, command):
                    # Decrypted SQL/archive exists only in the pipe.
                    decrypt=subprocess.Popen(['age','--decrypt','-i',str(key),str(parts[part].path)],
                        stdout=subprocess.PIPE,stderr=subprocess.DEVNULL)
                    try:
                        restored=subprocess.run(command,stdin=decrypt.stdout,stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE,timeout=60)
                        decrypt.stdout.close()
                        self.assertEqual(decrypt.wait(timeout=10),0)
                        self.assertEqual(restored.returncode,0,restored.stderr.decode())
                    finally:
                        if decrypt.poll() is None: decrypt.kill(); decrypt.wait()
                        decrypt.stdout.close()
                restore('roles',['psql',*target,'-d','postgres','-v','ON_ERROR_STOP=1'])
                restore('database',['pg_restore',*target,'--exit-on-error','--create','-d','postgres'])
                def query(connection, sql):
                    return run(['psql',*connection,'-d','sentinel_fixture','-XAt','-v','ON_ERROR_STOP=1'],input=sql).decode().strip()
                self.assertEqual(query(target,b'SELECT count(*) FROM public.fixture;'),'2')
                self.assertEqual(query(target,b'SELECT count(*) FROM neon_auth.fixture;'),'1')
                self.assertEqual(query(target,b"SELECT pg_get_userbyid(relowner),relforcerowsecurity FROM pg_class WHERE oid='public.fixture'::regclass;"),'fixture_owner|t')
                self.assertEqual(query(target,b'SET ROLE fixture_reader; SELECT count(*) FROM public.fixture;'),'SET\n1')
                denied=subprocess.run(['psql',*target,'-d','sentinel_fixture','-v','ON_ERROR_STOP=1'],
                    input=b'SET ROLE fixture_reader; INSERT INTO public.fixture VALUES (3,\'denied\');',
                    stdout=subprocess.PIPE,stderr=subprocess.PIPE)
                self.assertNotEqual(denied.returncode,0)
                for sql in (b"SELECT pg_get_expr(polqual,polrelid) FROM pg_policy ORDER BY polname;",
                            b"SELECT defaclacl::text FROM pg_default_acl ORDER BY oid;",
                            b"SELECT rolname,rolcanlogin,rolbypassrls FROM pg_roles WHERE rolname LIKE 'fixture_%' ORDER BY rolname;"):
                    self.assertEqual(query(source,sql),query(target,sql))
                self.assertEqual(set(p.name for p in output.iterdir()), {'database.pgdump.age','roles.sql.age'})
            finally:
                for data in reversed(clusters):
                    subprocess.run(['pg_ctl','-D',str(data),'-m','immediate','-w','stop'],
                                   stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=30)

if __name__=='__main__': unittest.main()
