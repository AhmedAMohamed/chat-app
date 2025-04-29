const ldap = require('ldapjs');

async function authenticateLDAPUser(ldapUrl, searchBase, usernameAttribute, username, password) {
  const client = ldap.createClient({ url: ldapUrl });

  try {
    // 1. Find the user's DN
    const userDN = await findUserDN(client, searchBase, usernameAttribute, username);

    if (!userDN) {
      console.log('User not found in LDAP.');
      return false; // Authentication failed
    }

    // 2. Attempt to bind with the user's DN and password
    const bindSuccessful = await attemptBind(client, userDN, password);
    return bindSuccessful;

  } catch (error) {
    console.error('LDAP Authentication Error:', error);
    return false; // Authentication failed due to an error
  } finally {
    client.unbind((err) => {
      if (err) console.error('Error unbinding LDAP client:', err);
    });
  }
}

async function findUserDN(client, searchBase, usernameAttribute, username) {
  return new Promise((resolve, reject) => {
    const searchFilter = `(&(objectClass=person)(${usernameAttribute}=${username}))`; // Adjust filter as needed

    client.search(searchBase, {
      filter: searchFilter,
      scope: 'sub',
      attributes: ['dn'],
      sizeLimit: 1,
    }, (err, res) => {
      if (err) {
        console.error('Error searching for user DN:', err);
        reject(err);
        return;
      }

      let userDN = null;
      res.on('searchEntry', (entry) => {
        userDN = entry.object.dn;
      });
      res.on('error', (searchErr) => {
        console.error('LDAP search error:', searchErr);
        reject(searchErr);
        return;
      });
      res.on('end', (result) => {
        if (result.status === 0 && userDN) {
          resolve(userDN);
        } else {
          resolve(null); // User not found
        }
      });
    });
  });
}

async function attemptBind(client, userDN, password) {
  return new Promise((resolve, reject) => {
    client.bind(userDN, password, (err) => {
      if (err) {
        console.error('LDAP bind error (authentication failed):', err);
        resolve(false); // Authentication failed
      } else {
        console.log('LDAP bind successful.');
        resolve(true); // Authentication successful
      }
    });

    client.on('error', (clientErr) => {
      console.error('LDAP client error during bind:', clientErr);
      reject(clientErr);
    });
  });
}

// Example usage within your application's login route:
async function handleLogin(req, res) {
  const { username, password } = req.body; // Assuming you get these from a form

  const ldapUrl = 'ldap://your-ldap-server.com:389'; // Replace with your LDAP URL
  const searchBase = 'ou=users,dc=example,dc=com'; // Replace with your user search base
  const usernameAttribute = 'uid'; // Replace with the attribute used for usernames (e.g., 'uid', 'cn', 'sAMAccountName')

  const isAuthenticated = await authenticateLDAPUser(ldapUrl, searchBase, usernameAttribute, username, password);

  if (isAuthenticated) {
    // Authentication successful - create a session for the user
    req.session.isAuthenticated = true;
    req.session.username = username; // Or store other relevant user info
    res.redirect('/dashboard'); // Redirect to a protected area
  } else {
    // Authentication failed - display an error message
    res.render('login', { error: 'Invalid username or password' });
  }
}

// In your route handler (e.g., using Express.js):
// app.post('/login', handleLogin);
