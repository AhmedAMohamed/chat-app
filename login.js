const ldap = require('ldapjs');

// LDAP server details
const ldapServerUrl = 'ldaps://172.16.25.5:636'; // Replace with your LDAP server URL
const bindDn = 'cn=read-only-admin,dc=emirate,dc=net'; // Replace with the DN to bind with
const bindCredentials = 'password'; // Replace with the password for the bind DN

// Create an LDAP client
const client = ldap.createClient({
  url: ldapServerUrl,
  tlsOptions: {
    rejectUnauthorized: false,
    ca: [fs.readFileSync('./s.crt')]
  }
});

// Bind to the LDAP server
client.bind(bindDn, bindCredentials, (err) => {
  if (err) {
    console.error('Bind Error:', err);
  } else {
    console.log('Successfully bound to the LDAP server!');

    // You can now perform other LDAP operations with this authenticated client

    // For example, searching:
    const searchOptions = {
      filter: '(objectClass=person)',
      scope: 'sub',
      attributes: ['cn', 'sn']
    };

    client.search('dc=example,dc=org', searchOptions, (err, res) => {
      if (err) {
        console.error('Search Error:', err);
      } else {
        console.log('Search Results:');
        res.on('searchEntry', (entry) => {
          console.log('  entry:', entry.object);
        });
        res.on('searchReference', (referral) => {
          console.log('  referral:', referral.uris.join());
        });
        res.on('end', (result) => {
          console.log('  search end status:', result.status);
          client.unbind((err) => {
            if (err) {
              console.error('Unbind Error:', err);
            } else {
              console.log('Successfully unbound from the LDAP server.');
            }
          });
        });
        res.on('error', (err) => {
          console.error('Search Error:', err);
        });
      }
    });
  }
});

// Handle client errors
client.on('error', (err) => {
  console.error('Client Error:', err);
});