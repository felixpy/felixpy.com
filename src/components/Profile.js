import React from 'react';
import PropTypes from 'prop-types';
import { withStyles } from '@material-ui/core/styles';
import Card from '@material-ui/core/Card';
import CardHeader from '@material-ui/core/CardHeader';
import CardMedia from '@material-ui/core/CardMedia';
import CardContent from '@material-ui/core/CardContent';
import CardActions from '@material-ui/core/CardActions';
import Avatar from '@material-ui/core/Avatar';
import IconButton from '@material-ui/core/IconButton';
import Typography from '@material-ui/core/Typography';
import { faCodeBranch, faCode } from '@fortawesome/free-solid-svg-icons';
import {
  faGithub,
  faTwitter,
  faFacebook,
  fa500px,
} from '@fortawesome/free-brands-svg-icons';
import { faTree } from '@fortawesome/free-solid-svg-icons';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import avatar from '../static/images/avatar.jpg';
import keyboard from '../static/images/keyboard.jpg';

const styles = (theme) => ({
  card: {
    maxWidth: 400,
    margin: '50px auto 0 auto',
  },
  media: {
    height: 0,
    paddingTop: '56.25%', // 16:9
  },
  actions: {
    display: 'flex',
  },
});

class Profile extends React.Component {
  render() {
    const { classes } = this.props;

    return (
      <Card className={classes.card}>
        <CardHeader
          avatar={
            <Avatar
              alt="Felix"
              aria-label="Felix"
              className={classes.avatar}
              src={avatar}
            />
          }
          title="Felix Yang"
          subheader="Software Engineer, Beijing"
        />
        <CardMedia
          className={classes.media}
          image={keyboard}
          title="Keyboard"
        />
        <CardContent>
          <Typography component="p">
            <span>Try it yourself. 👇👇👇</span>
          </Typography>
        </CardContent>
        <CardActions className={classes.actions} disableActionSpacing>
          <IconButton
            target="_blank"
            href="//github.com/felixpy"
            aria-label="Github"
          >
            <FontAwesomeIcon icon={faGithub} />
          </IconButton>
          <IconButton
            target="_blank"
            href="//github.com/openfext"
            aria-label="FEXT Github"
          >
            <FontAwesomeIcon icon={faCodeBranch} />
          </IconButton>
          <IconButton
            target="_blank"
            href="//felixpy.github.io"
            aria-label="Blog"
          >
            <FontAwesomeIcon icon={faTree} />
          </IconButton>
          <IconButton
            target="_blank"
            href="//openfext.github.io/docs"
            aria-label="FEXT Docs"
          >
            <FontAwesomeIcon icon={faCode} />
          </IconButton>
          {/* <IconButton
            target="_blank"
            href="//500px.com/gofelixpy"
            aria-label="500px"
          >
            <FontAwesomeIcon icon={fa500px} />
          </IconButton>
          <IconButton
            target="_blank"
            href="//twitter.com/gofelixpy"
            aria-label="Twitter"
          >
            <FontAwesomeIcon icon={faTwitter} />
          </IconButton>
          <IconButton
            target="_blank"
            href="//facebook.com/felixpy.1993"
            aria-label="Facebook"
          >
            <FontAwesomeIcon icon={faFacebook} />
          </IconButton> */}
        </CardActions>
      </Card>
    );
  }
}

Profile.propTypes = {
  classes: PropTypes.object.isRequired,
};

export default withStyles(styles)(Profile);
